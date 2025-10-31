#!/usr/bin/env python3
"""
FDO Chunker
Complete AOLBUF.AOL emulator for chunking FDO scripts into P3 payloads
Based on reverse engineering of the actual AOLBUF.AOL module
"""

import asyncio
from typing import List, Dict, Any, Tuple
import logging
import re

from fdo_daemon_client import FdoDaemonClient, FdoDaemonError
from fdo_atom_parser import FdoAtomParser
from p3_payload_builder import P3PayloadBuilder
from fdo_manual_compiler import FdoManualCompiler

logger = logging.getLogger(__name__)

class FdoChunkingError(Exception):
    """Errors specific to FDO chunking operations"""
    pass

class FdoChunker:
    """
    Complete AOLBUF.AOL emulator for chunking FDO scripts into P3 payloads.
    Leverages AtomForge's FDO daemon for high-performance per-atom compilation.
    """

    def __init__(self, daemon_client):
        """
        Initialize chunker with FDO daemon client.

        Args:
            daemon_client: Client for communicating with FDO compilation daemon
                          (FdoDaemonClient or FdoDaemonPoolClient)
        """
        self.daemon_client = daemon_client
        self.parser = FdoAtomParser()
        self.payload_builder = P3PayloadBuilder()

    async def process_fdo_script(self, fdo_script: str, stream_id: int = 0, token: str = 'AT') -> Dict[str, Any]:
        """
        Process FDO script into P3 payload chunks with continuation metadata.

        Args:
            fdo_script: FDO script text with atoms/action blocks
            stream_id: Stream identifier (varies by token)
            token: 2-byte token identifying packet type

        Returns:
            Dict containing:
            - 'chunks': List of P3 payload bytes
            - 'chunk_info': List of dicts with continuation metadata
            These are ready for P3 to wrap with header/CRC

        Raises:
            FdoChunkingError: If chunking fails
            ValueError: If parameters are invalid
        """
        logger.info(f"Processing FDO script for chunking: token={token}, stream_id={stream_id}")

        # Token validation removed - P3PayloadBuilder handles unknown tokens with fallback

        # Parse FDO preserving action blocks as atomic units
        try:
            atom_units = self.parser.parse_preserving_actions(fdo_script)
        except Exception as e:
            raise FdoChunkingError(f"Failed to parse FDO script: {e}")

        if not atom_units:
            logger.warning("No atom units found in FDO script")
            return []

        # Initialize packet assembly
        current_packet_data = bytearray()
        packets = []
        chunk_info = []  # Track continuation metadata

        # Header size is constant for all packets with same token
        header_size = self.payload_builder.get_header_size(token)
        max_payload_per_packet = P3PayloadBuilder.MAX_OUTBOUND_SIZE - header_size

        if max_payload_per_packet <= 0:
            raise FdoChunkingError(f"Token '{token}' header too large for any payload")

        logger.debug(f"Header size: {header_size}, max payload per packet: {max_payload_per_packet}")

        # Track sequence state for continuation detection
        in_segmented_sequence = False

        # Process each atom unit
        for i, unit in enumerate(atom_units):
            try:
                # Check if this is a raw_data atom (needs multi-frame splitting)
                if unit.get('is_raw_data'):
                    # Flush any pending data before adding raw_data packets
                    if current_packet_data:
                        packet = self.payload_builder.build_packet(
                            bytes(current_packet_data), stream_id, token
                        )
                        packets.append(packet)
                        chunk_info.append({
                            'size': len(packet),
                            'is_continuation': in_segmented_sequence,
                            'sequence_index': len(packets) - 1
                        })
                        logger.debug(f"Flushed packet {len(packets)} before raw_data: {len(packet)} bytes")
                        current_packet_data = bytearray()

                    # raw_data atoms split into multiple independent frames
                    # Each frame gets 000576 prefix
                    raw_data_packets = self._compile_raw_data_to_chunks(unit, stream_id, token)

                    # Add all packets (each is already complete with headers)
                    for packet in raw_data_packets:
                        packets.append(packet)
                        chunk_info.append({
                            'size': len(packet),
                            'is_continuation': False,  # Independent frames
                            'sequence_index': len(packets) - 1
                        })

                    # Skip normal processing for this unit
                    continue

                # Normal FDO atom processing - compile the atom unit using the daemon
                compiled_data = await self._compile_unit(unit)

                # Check if this atom is too large to ever fit (warn but continue)
                if unit['is_action'] and len(compiled_data) > P3PayloadBuilder.MAX_SEGMENT_SIZE:
                    logger.warning(
                        f"Action block at line {unit['line_start']} exceeds {P3PayloadBuilder.MAX_SEGMENT_SIZE} "
                        f"bytes ({len(compiled_data)} bytes): {unit['content'][:50]}..."
                    )

                # Segment if needed (with continuation markers)
                segments = self.payload_builder.segment_data_if_needed(compiled_data)
                logger.debug(f"Unit {i}: {len(compiled_data)} bytes -> {len(segments)} segments")

                # Handle segments based on whether they have continuation markers
                if len(segments) > 1:
                    # Unit was segmented - each segment must become its own packet
                    # First flush any existing packet data
                    if current_packet_data:
                        packet = self.payload_builder.build_packet(
                            bytes(current_packet_data), stream_id, token
                        )
                        packets.append(packet)
                        chunk_info.append({
                            'size': len(packet),
                            'is_continuation': in_segmented_sequence,
                            'sequence_index': len(packets) - 1
                        })
                        logger.debug(f"Flushed packet {len(packets)} before segmented unit: {len(packet)} bytes")
                        current_packet_data = bytearray()

                    # Each segment becomes its own packet
                    for j, segment in enumerate(segments):
                        packet = self.payload_builder.build_packet(segment, stream_id, token)
                        packets.append(packet)

                        # First segment starts a new sequence, subsequent segments are continuations
                        is_continuation = j > 0 or in_segmented_sequence
                        chunk_info.append({
                            'size': len(packet),
                            'is_continuation': is_continuation,
                            'sequence_index': len(packets) - 1
                        })
                        logger.debug(f"Segmented packet {len(packets)} (segment {j}): {len(packet)} bytes, continuation: {is_continuation}")

                    # After segmentation, we're in a segmented sequence
                    in_segmented_sequence = True
                else:
                    # Single segment - try to pack with other data
                    segment = segments[0]
                    space_needed = len(current_packet_data) + len(segment)

                    if space_needed > max_payload_per_packet:
                        # Must flush current packet
                        if current_packet_data:
                            packet = self.payload_builder.build_packet(
                                bytes(current_packet_data), stream_id, token
                            )
                            packets.append(packet)
                            chunk_info.append({
                                'size': len(packet),
                                'is_continuation': in_segmented_sequence,
                                'sequence_index': len(packets) - 1
                            })
                            logger.debug(f"Flushed packet {len(packets)}: {len(packet)} bytes, continuation: {in_segmented_sequence}")
                            current_packet_data = bytearray()

                    # Add segment to current packet
                    current_packet_data.extend(segment)

            except FdoDaemonError as e:
                raise FdoChunkingError(f"Compilation failed for atom at line {unit['line_start']}: {e}")
            except Exception as e:
                raise FdoChunkingError(f"Processing failed for atom at line {unit['line_start']}: {e}")

        # Flush any remaining data
        if current_packet_data:
            packet = self.payload_builder.build_packet(
                bytes(current_packet_data), stream_id, token
            )
            packets.append(packet)
            chunk_info.append({
                'size': len(packet),
                'is_continuation': in_segmented_sequence,
                'sequence_index': len(packets) - 1
            })
            logger.debug(f"Final packet {len(packets)}: {len(packet)} bytes, continuation: {in_segmented_sequence}")

        logger.info(f"Chunking complete: {len(packets)} packets generated")
        return {
            'chunks': packets,
            'chunk_info': chunk_info
        }

    async def _compile_unit(self, unit: Dict[str, Any]) -> bytes:
        """
        Compile atom unit using manual compiler or FDO daemon fallback.

        Args:
            unit: Atom unit from parser

        Returns:
            Compiled binary data

        Raises:
            FdoDaemonError: If compilation fails
        """
        try:
            # Try manual compilation first (400x faster for hex-pair atoms)
            if FdoManualCompiler.can_compile_manually(unit['content']):
                manual_result = FdoManualCompiler.compile_line(unit['content'])
                if manual_result is not None:
                    logger.debug(f"Manually compiled unit at line {unit['line_start']}: {len(manual_result)} bytes")
                    return manual_result
                else:
                    logger.warning(f"Manual compilation returned None, falling back to daemon for line {unit['line_start']}")

            # Fallback to daemon compilation
            result = await asyncio.to_thread(
                self.daemon_client.compile_source,
                unit['content']
            )

            logger.debug(f"Daemon compiled unit at line {unit['line_start']}: {len(result)} bytes")
            return result

        except Exception as e:
            logger.error(f"Compilation failed for unit: {unit['content'][:100]}...")
            raise

    def _compile_raw_data_to_chunks(self, unit: Dict[str, Any], stream_id: int, token: str) -> List[bytes]:
        """
        Compile raw_data atom into multiple P3 packets (≤128 bytes payload each).
        Each packet independently has the 000576 NON-FDO prefix.

        Based on wire format analysis:
        - Max payload: 128 bytes
        - Structure: Token(2) + StreamID(2) + 000576(3) + RawData(≤121)

        Args:
            unit: Atom unit with raw_data content
            stream_id: Stream ID for P3 packets
            token: Token type for P3 packets

        Returns:
            List of complete P3 packet bytes

        Raises:
            FdoChunkingError: If format is invalid
        """
        # Extract hex from raw_data <"hex"> format
        match = re.search(r'raw_data\s*<\s*"([A-Fa-f0-9]+)"\s*>', unit['content'])
        if not match:
            raise FdoChunkingError(
                f"Invalid raw_data format at line {unit['line_start']}: {unit['content'][:100]}"
            )

        hex_string = match.group(1)

        # Convert hex to binary
        try:
            raw_binary = bytes.fromhex(hex_string)
        except ValueError as e:
            raise FdoChunkingError(
                f"Invalid hex in raw_data at line {unit['line_start']}: {e}"
            )

        # Calculate max data per frame
        # Max payload: 128 bytes (from wire format analysis)
        MAX_PAYLOAD = 128
        header_size = self.payload_builder.get_header_size(token)  # AT = 4 bytes
        prefix_size = 3  # 000576
        max_data_per_frame = MAX_PAYLOAD - header_size - prefix_size  # 121 bytes for AT

        if max_data_per_frame <= 0:
            raise FdoChunkingError(
                f"Token '{token}' header too large for raw_data frames"
            )

        # Split raw_binary into chunks, each gets 000576 prefix
        packets = []
        offset = 0

        while offset < len(raw_binary):
            # Get chunk (max 121 bytes for AT token)
            chunk_size = min(max_data_per_frame, len(raw_binary) - offset)
            chunk = raw_binary[offset:offset + chunk_size]

            # Add 000576 prefix to THIS chunk (each frame is independent)
            prefixed_chunk = b'\x00\x05\x76' + chunk

            # Build P3 packet (adds token + stream_id header)
            packet = self.payload_builder.build_packet(prefixed_chunk, stream_id, token)
            packets.append(packet)

            offset += chunk_size

            logger.debug(
                f"raw_data frame {len(packets)}: {len(chunk)} bytes + 3-byte prefix "
                f"= {len(prefixed_chunk)} bytes payload → {len(packet)} bytes packet"
            )

        logger.info(
            f"Split raw_data at line {unit['line_start']}: {len(raw_binary)} bytes → "
            f"{len(packets)} frames (max {max_data_per_frame} bytes/frame)"
        )

        return packets

    async def validate_script(self, fdo_script: str) -> Dict[str, Any]:
        """
        Validate FDO script by attempting full compilation.

        Args:
            fdo_script: FDO script to validate

        Returns:
            Validation result dict
        """
        logger.info("Validating FDO script")

        # First, do syntax validation
        syntax_result = self.parser.validate_fdo_syntax(fdo_script)

        # Then try full compilation
        compilation_result = {'success': False, 'error': None, 'size': 0}
        try:
            compiled_data = await asyncio.to_thread(
                self.daemon_client.compile_source,
                fdo_script
            )
            compilation_result = {
                'success': True,
                'error': None,
                'size': len(compiled_data)
            }
            logger.info(f"Script validation successful: {len(compiled_data)} bytes")

        except FdoDaemonError as e:
            compilation_result['error'] = f"Compilation failed: {e}"
            logger.warning(f"Script validation failed: {e}")
        except Exception as e:
            compilation_result['error'] = f"Validation error: {e}"
            logger.error(f"Script validation error: {e}")

        return {
            'syntax': syntax_result,
            'compilation': compilation_result,
            'overall_valid': syntax_result['valid'] and compilation_result['success']
        }

    def estimate_chunks(self, fdo_script: str, token: str = 'AT') -> Dict[str, Any]:
        """
        Estimate chunking results without actually performing compilation.

        Args:
            fdo_script: FDO script to analyze
            token: Token type for estimation

        Returns:
            Estimation results
        """
        try:
            atom_units = self.parser.parse_preserving_actions(fdo_script)
            header_size = self.payload_builder.get_header_size(token)
            max_payload_per_packet = P3PayloadBuilder.MAX_OUTBOUND_SIZE - header_size

            # Rough estimation based on content length
            estimated_total_size = sum(len(unit['content'].encode('utf-8')) for unit in atom_units)
            estimated_chunks = self.payload_builder.estimate_chunk_count(estimated_total_size, token)

            return {
                'atom_units': len(atom_units),
                'action_blocks': sum(1 for u in atom_units if u['is_action']),
                'estimated_compiled_size': estimated_total_size,
                'estimated_chunks': max(1, estimated_chunks),
                'header_size': header_size,
                'max_payload_per_packet': max_payload_per_packet
            }

        except Exception as e:
            logger.error(f"Estimation failed: {e}")
            return {
                'error': str(e),
                'atom_units': 0,
                'estimated_chunks': 0
            }

    async def chunk_and_validate(self, fdo_script: str, stream_id: int = 0, token: str = 'AT',
                                validate_first: bool = True) -> Dict[str, Any]:
        """
        Complete chunking workflow with optional pre-validation.

        Args:
            fdo_script: FDO script to chunk
            stream_id: Stream identifier
            token: Token type
            validate_first: Whether to validate before chunking

        Returns:
            Complete results including chunks and validation
        """
        result = {
            'success': False,
            'chunks': [],
            'validation': None,
            'error': None,
            'stats': {}
        }

        try:
            # Optional pre-validation
            if validate_first:
                validation = await self.validate_script(fdo_script)
                result['validation'] = validation

                if not validation['overall_valid']:
                    result['error'] = "Script validation failed"
                    return result

            # Perform chunking
            chunk_result = await self.process_fdo_script(fdo_script, stream_id, token)
            chunks = chunk_result['chunks']
            chunk_info = chunk_result['chunk_info']

            # Calculate statistics
            stats = {
                'chunk_count': len(chunks),
                'total_size': sum(len(chunk) for chunk in chunks),
                'average_chunk_size': sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0,
                'header_size': self.payload_builder.get_header_size(token),
                'token': token,
                'stream_id': stream_id,
                'continuation_count': sum(1 for info in chunk_info if info['is_continuation'])
            }

            result.update({
                'success': True,
                'chunks': chunks,
                'chunk_info': chunk_info,
                'stats': stats
            })

            logger.info(f"Chunking completed successfully: {stats['chunk_count']} chunks, {stats['total_size']} total bytes")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Chunking workflow failed: {e}")

        return result