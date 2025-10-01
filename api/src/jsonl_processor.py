#!/usr/bin/env python3
"""
JSONL P3 Frame Processor
Processes JSONL files containing P3 frame data to extract and reassemble FDO streams
"""

import json
import logging
import time
import psutil
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from fdo_detector import FdoDetector
from fdo_daemon_client import FdoDaemonClient, FdoDaemonError

logger = logging.getLogger(__name__)

@dataclass
class P3Frame:
    """Represents a parsed P3 frame from JSONL"""
    timestamp: float
    full_hex: str
    token: Optional[str] = None
    direction: Optional[str] = None
    original_line: Dict[str, Any] = None

@dataclass
class FdoExtraction:
    """Represents extracted FDO data from a P3 frame"""
    frame: P3Frame
    fdo_data: bytes
    token: str
    stream_id: int
    fdo_size: int

class JsonlProcessingError(Exception):
    """Errors specific to JSONL processing operations"""
    pass

class JsonlProcessor:
    """
    Processor for JSONL files containing P3 frame data.
    Extracts FDO streams and reassembles them chronologically for decompilation.
    """

    # Safety limits for streaming processing
    MAX_FRAMES_LIMIT = 10_000_000      # Maximum frames to process (10M)
    MAX_PROCESSING_TIME = 1800         # Maximum processing time in seconds (30 minutes)
    MAX_MEMORY_MB = 4096               # Maximum memory usage in MB (4GB)
    MEMORY_CHECK_INTERVAL = 1000       # Check memory every N frames
    PROGRESS_LOG_INTERVAL = 10000      # Log progress every N frames

    @classmethod
    def parse_jsonl_frames(cls, jsonl_content: str) -> List[P3Frame]:
        """
        Parse JSONL content and extract P3 frame data.

        Args:
            jsonl_content: Raw JSONL file content

        Returns:
            List of parsed P3Frame objects

        Raises:
            JsonlProcessingError: If JSONL parsing fails
        """
        frames = []
        lines = jsonl_content.strip().split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            try:
                frame_data = json.loads(line)

                # Extract required fields
                full_hex = frame_data.get('fullHex', '')
                timestamp_str = frame_data.get('ts', '0')

                if not full_hex:
                    logger.warning(f"Line {line_num}: Missing fullHex field")
                    continue

                # Parse timestamp (handle string format like "1.759028162441E9")
                try:
                    timestamp = float(timestamp_str)
                except (ValueError, TypeError):
                    logger.warning(f"Line {line_num}: Invalid timestamp '{timestamp_str}'")
                    timestamp = 0.0

                frame = P3Frame(
                    timestamp=timestamp,
                    full_hex=full_hex.upper(),  # Normalize to uppercase
                    token=frame_data.get('token'),
                    direction=frame_data.get('dir'),
                    original_line=frame_data
                )

                frames.append(frame)

            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Invalid JSON - {e}")
                continue
            except Exception as e:
                logger.warning(f"Line {line_num}: Processing error - {e}")
                continue

        if not frames:
            raise JsonlProcessingError("No valid P3 frames found in JSONL content")

        logger.info(f"Parsed {len(frames)} P3 frames from {len(lines)} JSONL lines")
        return frames

    @classmethod
    def determine_chronological_order(cls, frames: List[P3Frame]) -> str:
        """
        Analyze timestamps to determine if frames are in chronological order.

        Args:
            frames: List of P3Frame objects

        Returns:
            "oldest_first" or "newest_first"
        """
        if len(frames) < 2:
            return "oldest_first"  # Default for single frame

        # Compare first and last timestamps
        first_ts = frames[0].timestamp
        last_ts = frames[-1].timestamp

        if first_ts <= last_ts:
            return "oldest_first"
        else:
            return "newest_first"

    @classmethod
    def extract_fdo_from_frames(cls, frames: List[P3Frame]) -> List[FdoExtraction]:
        """
        Extract FDO data from P3 frames with known token types.

        Args:
            frames: List of P3Frame objects

        Returns:
            List of FdoExtraction objects with successfully extracted FDO data
        """
        extractions = []

        for frame in frames:
            try:
                # Convert hex string to bytes
                if len(frame.full_hex) % 2 != 0:
                    logger.warning(f"Frame with timestamp {frame.timestamp}: Odd-length hex string")
                    continue

                frame_bytes = bytes.fromhex(frame.full_hex)

                # Use existing FDO detector
                detection_result = FdoDetector.detect_fdo_in_p3_frame(frame_bytes)

                if detection_result['success'] and detection_result['fdo_detected']:
                    fdo_metadata = detection_result['fdo_metadata']
                    fdo_data_raw = detection_result['fdo_data']

                    # FDO data from detect_fdo_in_p3_frame is already raw bytes, not base64
                    fdo_data = fdo_data_raw if isinstance(fdo_data_raw, bytes) else bytes(fdo_data_raw)

                    extraction = FdoExtraction(
                        frame=frame,
                        fdo_data=fdo_data,
                        token=fdo_metadata['token'],
                        stream_id=fdo_metadata['stream_id'],
                        fdo_size=fdo_metadata['fdo_size']
                    )

                    extractions.append(extraction)
                    logger.debug(f"Extracted FDO from frame: token={extraction.token}, "
                               f"stream_id={extraction.stream_id}, size={extraction.fdo_size}")
                else:
                    # Log why detection failed (if we have error info)
                    if detection_result.get('error'):
                        logger.debug(f"Frame timestamp {frame.timestamp}: {detection_result['error']}")

            except Exception as e:
                logger.warning(f"Frame timestamp {frame.timestamp}: FDO extraction failed - {e}")
                continue

        logger.info(f"Successfully extracted FDO from {len(extractions)} out of {len(frames)} frames")
        return extractions

    @classmethod
    def reassemble_fdo_streams(cls, extractions: List[FdoExtraction],
                              chronological_order: str) -> bytes:
        """
        Reassemble FDO data from extractions in chronological order.

        Args:
            extractions: List of FdoExtraction objects
            chronological_order: "oldest_first" or "newest_first"

        Returns:
            Concatenated FDO data bytes ready for decompilation
        """
        if not extractions:
            return b''

        # Sort extractions by timestamp in chronological order
        if chronological_order == "oldest_first":
            sorted_extractions = sorted(extractions, key=lambda x: x.frame.timestamp)
        else:  # newest_first
            sorted_extractions = sorted(extractions, key=lambda x: x.frame.timestamp, reverse=True)

        # Concatenate FDO data
        reassembled_data = bytearray()
        for extraction in sorted_extractions:
            reassembled_data.extend(extraction.fdo_data)

        logger.info(f"Reassembled {len(sorted_extractions)} FDO segments into {len(reassembled_data)} bytes")
        logger.debug(f"Timestamp order: {sorted_extractions[0].frame.timestamp} -> {sorted_extractions[-1].frame.timestamp}")

        return bytes(reassembled_data)

    @classmethod
    def stream_process_file(cls, file_lines_iterator_factory) -> Dict[str, Any]:
        """
        Memory-efficient streaming processing of JSONL file.
        Processes frames one at a time without loading entire file into memory.
        Includes safety limits and memory monitoring.

        Args:
            file_lines_iterator_factory: Function that returns an iterator yielding JSONL lines

        Returns:
            Processing results with FDO data and metadata
        """
        result = {
            'success': False,
            'fdo_frames': None,
            'frames_processed': 0,
            'fdo_frames_found': 0,
            'total_fdo_bytes': 0,
            'chronological_order': 'unknown',
            'supported_tokens': set(),
            'error': None,
            'processing_time': None,
            'peak_memory_mb': None,
            'terminated_early': False
        }

        start_time = time.time()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory = initial_memory

        try:
            logger.info(f"Starting streaming JSONL processing (initial memory: {initial_memory:.1f} MB)")

            # Pass 1: Sample frames to determine chronological order
            logger.info("Pass 1: Determining chronological order from samples...")
            chronological_order, sample_frame_count = cls._determine_order_from_samples(file_lines_iterator_factory())
            result['chronological_order'] = chronological_order
            logger.info(f"Detected order: {chronological_order} (sampled {sample_frame_count} frames)")

            # Pass 2: Stream through file and process frames in order
            logger.info("Pass 2: Processing frames and extracting FDO data...")
            fdo_frames, processed_count, fdo_count, supported_tokens, early_termination = cls._stream_extract_fdo_data(
                file_lines_iterator_factory(), chronological_order, start_time
            )

            if early_termination:
                result['terminated_early'] = True
                result['error'] = early_termination

            # Update peak memory
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            peak_memory = max(peak_memory, current_memory)

            # Calculate total bytes from individual frames
            total_fdo_bytes = sum(len(frame['data']) for frame in fdo_frames) if fdo_frames else 0

            result.update({
                'success': True,
                'fdo_frames': fdo_frames,  # Individual frames for frame-by-frame decompilation
                'frames_processed': processed_count,
                'fdo_frames_found': fdo_count,
                'total_fdo_bytes': total_fdo_bytes,
                'supported_tokens': list(supported_tokens)
            })

            processing_time = time.time() - start_time
            result['processing_time'] = f"{processing_time:.3f}s"
            result['peak_memory_mb'] = f"{peak_memory:.1f} MB"

            logger.info(f"Streaming processing complete: {fdo_count} FDO frames from {processed_count} total frames, "
                       f"time: {processing_time:.3f}s, peak memory: {peak_memory:.1f} MB")

        except Exception as e:
            result['error'] = str(e)
            processing_time = time.time() - start_time
            result['processing_time'] = f"{processing_time:.3f}s"
            result['peak_memory_mb'] = f"{peak_memory:.1f} MB"
            logger.error(f"Streaming JSONL processing failed: {e}", exc_info=True)

        return result

    @classmethod
    def _determine_order_from_samples(cls, file_lines_iterator) -> tuple[str, int]:
        """
        Determine chronological order by sampling first and last frames.
        Memory-efficient approach that doesn't load entire file.

        Returns:
            Tuple of (chronological_order, sample_count)
        """
        first_timestamps = []
        last_timestamps = []
        sample_count = 0

        # Sample first 100 frames
        for line in file_lines_iterator:
            if sample_count >= 100:
                break

            frame = cls._parse_single_line(line, sample_count + 1)
            if frame:
                first_timestamps.append(frame.timestamp)
                sample_count += 1

        # Store position to sample from end (this is tricky with iterators)
        # For now, we'll use the simple heuristic that files are usually in order
        # TODO: Implement end-sampling for files that support seeking

        if len(first_timestamps) < 2:
            return "oldest_first", sample_count

        # Check if timestamps are generally increasing (oldest first) or decreasing (newest first)
        increasing_count = 0
        decreasing_count = 0

        for i in range(1, len(first_timestamps)):
            if first_timestamps[i] > first_timestamps[i-1]:
                increasing_count += 1
            elif first_timestamps[i] < first_timestamps[i-1]:
                decreasing_count += 1

        if increasing_count > decreasing_count:
            return "oldest_first", sample_count
        else:
            return "newest_first", sample_count

    @classmethod
    def _stream_extract_fdo_data(cls, file_lines_iterator, chronological_order: str, start_time: float) -> tuple[list, int, int, set, str]:
        """
        Stream through file and extract FDO data frame by frame.
        Returns individual FDO frames for frame-by-frame decompilation.
        Includes safety monitoring and early termination.

        Returns:
            Tuple of (fdo_frames_list, frames_processed, fdo_frames_found, supported_tokens, early_termination_reason)
        """
        fdo_data_parts = []
        frames_processed = 0
        fdo_frames_found = 0
        supported_tokens = set()
        process = psutil.Process()
        early_termination = None

        def check_safety_limits():
            """Check if we need to terminate early due to safety limits."""
            nonlocal early_termination

            # Check frame count limit
            if frames_processed >= cls.MAX_FRAMES_LIMIT:
                early_termination = f"Frame limit exceeded ({cls.MAX_FRAMES_LIMIT:,} frames)"
                return True

            # Check processing time limit
            if time.time() - start_time > cls.MAX_PROCESSING_TIME:
                early_termination = f"Processing time limit exceeded ({cls.MAX_PROCESSING_TIME} seconds)"
                return True

            # Check memory usage (only every N frames for performance)
            if frames_processed % cls.MEMORY_CHECK_INTERVAL == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                if current_memory > cls.MAX_MEMORY_MB:
                    early_termination = f"Memory limit exceeded ({current_memory:.1f} MB > {cls.MAX_MEMORY_MB} MB)"
                    return True

            return False

        # For oldest_first, we can process directly
        # For newest_first, we need to collect and reverse (but still memory-efficient)
        if chronological_order == "newest_first":
            # Collect FDO data in reverse order, then reverse the list
            temp_fdo_parts = []

            for line in file_lines_iterator:
                frames_processed += 1

                # Progress logging
                if frames_processed % cls.PROGRESS_LOG_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    logger.info(f"Processed {frames_processed:,} frames... ({elapsed:.1f}s, {memory_mb:.1f} MB)")

                # Safety checks
                if check_safety_limits():
                    logger.warning(f"Early termination: {early_termination}")
                    break

                frame = cls._parse_single_line(line, frames_processed)
                if frame:
                    fdo_data = cls._extract_fdo_from_single_frame(frame)
                    if fdo_data:
                        temp_fdo_parts.append(fdo_data)
                        supported_tokens.add(fdo_data['token'])
                        fdo_frames_found += 1

            # Reverse for newest_first order
            fdo_data_parts = list(reversed(temp_fdo_parts))
        else:
            # Process directly for oldest_first
            for line in file_lines_iterator:
                frames_processed += 1

                # Progress logging
                if frames_processed % cls.PROGRESS_LOG_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    logger.info(f"Processed {frames_processed:,} frames... ({elapsed:.1f}s, {memory_mb:.1f} MB)")

                # Safety checks
                if check_safety_limits():
                    logger.warning(f"Early termination: {early_termination}")
                    break

                frame = cls._parse_single_line(line, frames_processed)
                if frame:
                    fdo_data = cls._extract_fdo_from_single_frame(frame)
                    if fdo_data:
                        fdo_data_parts.append(fdo_data)
                        supported_tokens.add(fdo_data['token'])
                        fdo_frames_found += 1

        # Return individual FDO frames for frame-by-frame decompilation
        total_fdo_bytes = sum(len(fdo_info['data']) for fdo_info in fdo_data_parts)
        logger.info(f"Extracted {len(fdo_data_parts)} FDO segments totaling {total_fdo_bytes} bytes")
        return fdo_data_parts, frames_processed, fdo_frames_found, supported_tokens, early_termination

    @classmethod
    def _parse_single_line(cls, line: str, line_num: int) -> Optional[P3Frame]:
        """Parse a single JSONL line into a P3Frame object."""
        line = line.strip()
        if not line:
            return None

        try:
            frame_data = json.loads(line)

            full_hex = frame_data.get('fullHex', '')
            timestamp_str = frame_data.get('ts', '0')

            if not full_hex:
                return None

            try:
                timestamp = float(timestamp_str)
            except (ValueError, TypeError):
                timestamp = 0.0

            return P3Frame(
                timestamp=timestamp,
                full_hex=full_hex.upper(),
                token=frame_data.get('token'),
                direction=frame_data.get('dir'),
                original_line=frame_data
            )

        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    @classmethod
    def _extract_fdo_from_single_frame(cls, frame: P3Frame) -> Optional[Dict[str, Any]]:
        """Extract FDO data from a single frame."""
        try:
            if len(frame.full_hex) % 2 != 0:
                return None

            frame_bytes = bytes.fromhex(frame.full_hex)
            detection_result = FdoDetector.detect_fdo_in_p3_frame(frame_bytes)

            if detection_result['success'] and detection_result['fdo_detected']:
                fdo_metadata = detection_result['fdo_metadata']
                fdo_data_raw = detection_result['fdo_data']

                # FDO data is already raw bytes
                fdo_data = fdo_data_raw if isinstance(fdo_data_raw, bytes) else bytes(fdo_data_raw)

                return {
                    'token': fdo_metadata['token'],
                    'stream_id': fdo_metadata['stream_id'],
                    'data': fdo_data,
                    'original_frame_hex': frame.full_hex
                }

        except Exception:
            pass

        return None


    @classmethod
    def _decompile_frames_individually(cls, fdo_frames: list, daemon_client, daemon_manager=None) -> Dict[str, Any]:
        """
        Decompile FDO frames individually with enhanced crash detection and forensics.

        Args:
            fdo_frames: List of FDO frame dictionaries with 'data', 'token', 'stream_id'
            daemon_client: FDO daemon client for decompilation (FdoDaemonClient)
            daemon_manager: Optional daemon manager for restart capability (for single daemon mode)

        Returns:
            Dictionary with decompiled source and detailed crash analytics
        """
        frame_results = []  # Unified list tracking all frame processing results in order
        frames_decompiled_successfully = 0
        frames_failed_decompilation = 0
        daemon_restarts = 0
        frames_skipped_after_crash = 0

        # Check if we're using pool client (which has built-in resilience)
        is_pool_client = False  # We only use single daemon now

        logger.info(f"Starting enhanced frame-by-frame decompilation of {len(fdo_frames)} frames "
                   f"with crash forensics ({'pool mode' if is_pool_client else 'single daemon mode'})...")

        for i, frame_info in enumerate(fdo_frames):
            # Extract frame details for forensics
            fdo_data = frame_info['data']
            token = frame_info['token']
            stream_id = frame_info['stream_id']
            data_size = len(fdo_data)

            # Pre-frame forensic logging with expanded hex preview for searchability
            data_preview = fdo_data[:200].hex() if len(fdo_data) > 200 else fdo_data.hex()
            logger.debug(f"Frame {i}: token={token}, stream_id={stream_id}, size={data_size}, "
                        f"preview={data_preview}...")

            # With new daemon: no preemptive health checks needed
            # Daemon auto-recovers from Ada32 crashes, returns HTTP 500 instead of dying

            try:
                # Call daemon with individual frame
                source_code = daemon_client.decompile_binary(fdo_data)

                frame_results.append({
                    'result_type': 'success',
                    'index': i,
                    'token': token,
                    'stream_id': stream_id,
                    'source': source_code,
                    'size_bytes': len(fdo_data)
                })
                frames_decompiled_successfully += 1

                # Log progress every 100 frames
                if (i + 1) % 100 == 0:
                    logger.info(f"Decompiled {i + 1}/{len(fdo_frames)} frames successfully...")

            except FdoDaemonError as e:
                # Daemon returned error (HTTP 4xx/5xx)
                # HTTP 422 = unprocessable (non-FDO data like images, text)
                # HTTP 500 = Ada32 error (malformed FDO or unsupported format)
                error_str = str(e)
                logger.debug(f"Frame {i} decompilation failed (likely non-FDO): {error_str}")

                # Save forensics for analysis
                cls._save_crash_frame_forensics(i, frame_info, fdo_data, error_str)

                frame_results.append({
                    'result_type': 'crash_handled',
                    'index': i,
                    'token': token,
                    'stream_id': stream_id,
                    'error': error_str,
                    'size_bytes': data_size,
                    'data_preview': data_preview,
                    'full_hex': fdo_data.hex(),
                    'original_frame_hex': frame_info.get('original_frame_hex', '')
                })

                # Continue processing - daemon auto-reinitializes after crashes
                frames_failed_decompilation += 1
                continue

            except Exception as e:
                # Unexpected errors (connection issues, timeouts, etc.)
                error_str = str(e)
                is_daemon_crash = cls._is_daemon_crash_error(error_str)

                if is_daemon_crash and not is_pool_client:
                    # True daemon process crash (rare with new daemon - only Wine/process failures)
                    logger.error(f"🔥 DAEMON PROCESS CRASH! Frame {i} caused process failure: {error_str}")

                    # Save forensics for debugging
                    cls._save_crash_frame_forensics(i, frame_info, fdo_data, error_str)

                    frame_results.append({
                        'result_type': 'process_crash',
                        'index': i,
                        'token': token,
                        'stream_id': stream_id,
                        'error': error_str,
                        'size_bytes': data_size,
                        'data_preview': data_preview,
                        'full_hex': fdo_data.hex(),
                        'original_frame_hex': frame_info.get('original_frame_hex', '')
                    })

                    # Attempt daemon restart for true process crashes only
                    if daemon_manager and cls._restart_daemon_if_needed(daemon_manager, daemon_client):
                        daemon_restarts += 1
                        logger.info(f"Daemon restarted after process crash at frame {i}, continuing...")
                    else:
                        logger.error(f"Cannot restart daemon after process crash at frame {i}, stopping processing")
                        frames_skipped_after_crash = len(fdo_frames) - i - 1
                        break
                else:
                    # Normal decompilation failure or network error
                    frame_results.append({
                        'result_type': 'failure',
                        'index': i,
                        'token': token,
                        'stream_id': stream_id,
                        'error': error_str,
                        'size_bytes': data_size,
                        'data_preview': data_preview,
                        'original_frame_hex': frame_info.get('original_frame_hex', '')
                    })

                frames_failed_decompilation += 1
                logger.warning(f"Frame {i} decompilation failed: {error_str}")
                continue

        # Reassemble frame results into final source with compact failure comments
        reassembled_source = ""
        for result in frame_results:
            if result['result_type'] == 'success':
                # Include successful decompilation
                reassembled_source += f"// Frame {result['index']}: Successfully decompiled (Token: {result['token']}, Stream ID: {result['stream_id']}, Size: {result['size_bytes']} bytes)\n"
                reassembled_source += result['source'] + "\n\n"
            elif result['result_type'] == 'failure':
                # Include clean failure comment with FDO hex data (not full P3 frame)
                fdo_hex = result.get('full_hex', result.get('data_preview', ''))
                reassembled_source += f"// FAILED [{result['index']}] {result['token']} stream:{result['stream_id']} {result['size_bytes']}b : {fdo_hex}\n\n"
            elif result['result_type'] == 'crash_handled':
                # Non-FDO data (images, text, etc) - daemon returned HTTP 422/500
                fdo_hex = result.get('full_hex', result.get('data_preview', ''))
                reassembled_source += f"// NON-FDO [{result['index']}] {result['token']} stream:{result['stream_id']} {result['size_bytes']}b : {fdo_hex}\n\n"
            elif result['result_type'] == 'process_crash':
                # True daemon process crash (Wine/process failure - rare)
                fdo_hex = result.get('full_hex', result.get('data_preview', ''))
                reassembled_source += f"// DAEMON_CRASH [{result['index']}] {result['token']} stream:{result['stream_id']} {result['size_bytes']}b : {fdo_hex}\n\n"

        # Calculate failure rate
        total_frames = len(fdo_frames)
        failure_rate = (frames_failed_decompilation / total_frames * 100) if total_frames > 0 else 0

        # Extract separate lists for result analysis
        successful_decompilations = [r for r in frame_results if r['result_type'] == 'success']
        failed_frames = [r for r in frame_results if r['result_type'] == 'failure']
        ada32_crashes = [r for r in frame_results if r['result_type'] == 'crash_handled']
        process_crashes = [r for r in frame_results if r['result_type'] == 'process_crash']

        # Enhanced completion logging
        logger.info(f"Frame-by-frame decompilation complete: {frames_decompiled_successfully}/{total_frames} successful, "
                   f"{len(ada32_crashes)} non-FDO frames, {len(process_crashes)} daemon crashes, "
                   f"{daemon_restarts} daemon restarts, {frames_skipped_after_crash} frames skipped, {failure_rate:.1f}% failure rate")

        if ada32_crashes:
            logger.info(f"{len(ada32_crashes)} non-FDO frames (images, text, etc) skipped")
            for frame in ada32_crashes[:5]:  # Log first 5
                logger.info(f"   Frame {frame['index']}: {frame['token']} stream:{frame['stream_id']} "
                          f"{frame['size_bytes']}b")

        if process_crashes:
            logger.warning(f"{len(process_crashes)} frames caused daemon process crashes")
            for crash in process_crashes:
                logger.warning(f"   Frame {crash['index']}: {crash['token']} stream:{crash['stream_id']} "
                             f"{crash['size_bytes']}b")

        return {
            'source': reassembled_source.strip(),
            'frames_decompiled_successfully': frames_decompiled_successfully,
            'frames_failed_decompilation': frames_failed_decompilation,
            'decompilation_failure_rate': round(failure_rate, 2),
            'successful_decompilations': successful_decompilations,
            'failed_frames': failed_frames,
            'ada32_crashes': ada32_crashes,  # Frames that caused Ada32 crashes (handled gracefully)
            'process_crashes': process_crashes,  # Frames that caused true daemon process crashes
            'daemon_restarts': daemon_restarts,
            'frames_skipped_after_crash': frames_skipped_after_crash
        }

    @classmethod
    def _check_daemon_health(cls, daemon_client, frame_index: int) -> bool:
        """Check if daemon is alive and responding."""
        try:
            daemon_client.health()
            return True
        except Exception as e:
            logger.debug(f"Daemon health check failed at frame {frame_index}: {e}")
            return False

    @classmethod
    def _is_daemon_crash_error(cls, error_str: str) -> bool:
        """Determine if error indicates daemon crashed vs normal failure."""
        crash_indicators = [
            "Connection refused",
            "ConnectionRefusedError",
            "Failed to establish a new connection",
            "Connection aborted",
            "RemoteDisconnected",
            "ConnectionResetError"
        ]
        return any(indicator in error_str for indicator in crash_indicators)

    @classmethod
    def _restart_daemon_if_needed(cls, daemon_manager, daemon_client) -> bool:
        """Attempt to restart crashed daemon."""
        try:
            logger.info("Stopping crashed daemon...")
            daemon_manager.stop()

            logger.info("Starting fresh daemon...")
            daemon_manager.start()

            # Verify daemon is responsive
            daemon_client.health()
            logger.info("Daemon successfully restarted and verified healthy")
            return True
        except Exception as e:
            logger.error(f"Failed to restart daemon: {e}")
            return False

    @classmethod
    def _save_crash_frame_forensics(cls, frame_index: int, frame_info: dict, fdo_data: bytes, error: str):
        """Save detailed forensics of frame that failed decompilation (non-FDO data or error)."""
        try:
            import os
            forensics_dir = "/tmp/atomforge_forensics"
            os.makedirs(forensics_dir, exist_ok=True)

            # Save binary data
            failed_file = f"{forensics_dir}/failed_frame_{frame_index}.bin"
            with open(failed_file, "wb") as f:
                f.write(fdo_data)

            # Save metadata
            metadata_file = f"{forensics_dir}/failed_frame_{frame_index}_metadata.txt"
            with open(metadata_file, "w") as f:
                f.write(f"Failed Frame {frame_index} Forensics\n")
                f.write(f"{'='*50}\n")
                f.write(f"Token: {frame_info['token']}\n")
                f.write(f"Stream ID: {frame_info['stream_id']}\n")
                f.write(f"Data Size: {len(fdo_data)} bytes\n")
                f.write(f"Error: {error}\n")
                f.write(f"Hex Data: {fdo_data.hex()}\n")
                f.write(f"Binary saved to: {failed_file}\n")
                f.write(f"\nLikely non-FDO data (image, text, binary blob)\n")

            logger.debug(f"Failed frame forensics saved: {failed_file}")

        except Exception as e:
            logger.error(f"Failed to save frame forensics: {e}")

    @classmethod
    def process_jsonl_file(cls, jsonl_content: str) -> Dict[str, Any]:
        """
        Complete JSONL processing workflow.

        Args:
            jsonl_content: Raw JSONL file content

        Returns:
            Processing results with FDO data and metadata
        """
        result = {
            'success': False,
            'fdo_data': None,
            'frames_processed': 0,
            'fdo_frames_found': 0,
            'total_fdo_bytes': 0,
            'chronological_order': 'unknown',
            'supported_tokens': [],
            'error': None
        }

        try:
            # Step 1: Parse JSONL frames
            frames = cls.parse_jsonl_frames(jsonl_content)
            result['frames_processed'] = len(frames)

            # Step 2: Determine chronological order
            chronological_order = cls.determine_chronological_order(frames)
            result['chronological_order'] = chronological_order

            # Step 3: Extract FDO data from frames
            extractions = cls.extract_fdo_from_frames(frames)
            result['fdo_frames_found'] = len(extractions)

            if not extractions:
                result['error'] = "No FDO data found in any P3 frames"
                return result

            # Step 4: Reassemble FDO streams
            fdo_data = cls.reassemble_fdo_streams(extractions, chronological_order)
            result['fdo_data'] = fdo_data
            result['total_fdo_bytes'] = len(fdo_data)

            # Step 5: Collect metadata
            supported_tokens = list(set(extraction.token for extraction in extractions))
            result['supported_tokens'] = supported_tokens

            result['success'] = True
            logger.info(f"JSONL processing successful: {len(extractions)} FDO frames, "
                       f"{len(fdo_data)} total bytes, tokens: {supported_tokens}")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"JSONL processing failed: {e}", exc_info=True)

        return result