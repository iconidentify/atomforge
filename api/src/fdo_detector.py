#!/usr/bin/env python3
"""
FDO Detector
Auto-detection engine for identifying and extracting FDO data from P3 frames.
Combines P3 frame parsing with payload token analysis for real-time UI hints.
"""

from typing import Dict, Any, Optional
import logging
import base64

from p3_frame_parser import P3FrameParser, P3FrameParseError
from p3_payload_builder import P3PayloadBuilder

logger = logging.getLogger(__name__)

class FdoDetectionError(Exception):
    """Errors specific to FDO detection operations"""
    pass

class FdoDetector:
    """
    Auto-detection engine for FDO data within P3 frames.
    Optimized for real-time hint systems in frontend applications.
    """

    @classmethod
    def detect_fdo_in_p3_frame(cls, frame_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze P3 frame and attempt to detect/extract FDO data.

        Args:
            frame_bytes: Complete P3 frame bytes

        Returns:
            Detection result with extracted FDO data if found
        """
        result = {
            'success': False,
            'fdo_detected': False,
            'p3_frame_valid': False,
            'error': None,
            'p3_metadata': {},
            'fdo_metadata': {},
            'fdo_data': None
        }

        try:
            # Step 1: Parse P3 frame
            logger.debug("Parsing P3 frame...")
            p3_parsed = P3FrameParser.parse_frame(frame_bytes)

            result['success'] = True
            result['p3_frame_valid'] = True
            result['p3_metadata'] = {
                'packet_type': p3_parsed['packet_type'],
                'packet_type_value': p3_parsed['packet_type_value'],
                'tx_seq': p3_parsed['tx_seq'],
                'rx_seq': p3_parsed['rx_seq'],
                'data_length': p3_parsed['data_length'],
                'frame_size': p3_parsed['frame_size'],
                'client_packet': p3_parsed['client_packet']
            }

            # Only attempt FDO detection on DATA packets
            if p3_parsed['packet_type_value'] != 0x20:  # Not a DATA packet
                result['error'] = f"Not a DATA packet (type: {p3_parsed['packet_type']})"
                logger.debug(f"Skipping FDO detection: {result['error']}")
                return result

            payload_data = p3_parsed['data']
            if not payload_data:
                result['error'] = "No payload data in P3 frame"
                logger.debug(result['error'])
                return result

            # Step 2: Attempt FDO detection on payload
            logger.debug(f"Attempting FDO detection on {len(payload_data)} byte payload...")
            fdo_result = cls._detect_fdo_in_payload(payload_data)

            if fdo_result['fdo_detected']:
                result['fdo_detected'] = True
                result['fdo_metadata'] = fdo_result['fdo_metadata']
                result['fdo_data'] = fdo_result['fdo_data']
                logger.info(f"FDO detected: token={fdo_result['fdo_metadata']['token']}, "
                           f"stream_id={fdo_result['fdo_metadata']['stream_id']}, "
                           f"fdo_size={fdo_result['fdo_metadata']['fdo_size']}")
            else:
                result['error'] = fdo_result.get('error', 'FDO not detected')
                logger.debug(f"FDO not detected: {result['error']}")

            return result

        except P3FrameParseError as e:
            result['error'] = f"P3 frame parsing failed: {str(e)}"
            logger.warning(result['error'])
            return result

        except Exception as e:
            result['error'] = f"Unexpected error during detection: {str(e)}"
            logger.error(result['error'], exc_info=True)
            return result

    @classmethod
    def _detect_fdo_in_payload(cls, payload_data: bytes) -> Dict[str, Any]:
        """
        Attempt to detect FDO data within P3 payload using existing token parser.

        Args:
            payload_data: Raw P3 payload bytes

        Returns:
            FDO detection result
        """
        result = {
            'fdo_detected': False,
            'error': None,
            'fdo_metadata': {},
            'fdo_data': None
        }

        try:
            # Use existing P3PayloadBuilder to parse token structure
            parsed_payload = P3PayloadBuilder.parse_packet_header(payload_data)

            # If we got here, token parsing succeeded
            token = parsed_payload['token']
            stream_id = parsed_payload['stream_id']
            fdo_data = parsed_payload['data']

            result['fdo_detected'] = True
            result['fdo_metadata'] = {
                'token': token,
                'stream_id': stream_id,
                'header_size': parsed_payload['header_size'],
                'fdo_size': parsed_payload['data_size'],
                'total_payload_size': len(payload_data)
            }
            result['fdo_data'] = fdo_data

            logger.debug(f"FDO payload parsed successfully: token={token}, stream_id={stream_id}, "
                        f"fdo_size={len(fdo_data)}")

            return result

        except ValueError as e:
            # P3PayloadBuilder.parse_packet_header raises ValueError for invalid tokens/data
            result['error'] = f"Invalid FDO token structure: {str(e)}"
            logger.debug(result['error'])
            return result

        except Exception as e:
            result['error'] = f"Payload parsing error: {str(e)}"
            logger.debug(result['error'])
            return result


    @classmethod
    def detect_from_base64(cls, base64_frame: str) -> Dict[str, Any]:
        """
        Detect FDO data from base64-encoded P3 frame.

        Args:
            base64_frame: Base64-encoded P3 frame data

        Returns:
            Detection result with base64-encoded FDO data if found
        """
        try:
            # Decode base64 frame
            frame_bytes = base64.b64decode(base64_frame)

            # Perform detection
            result = cls.detect_fdo_in_p3_frame(frame_bytes)

            # Encode FDO data as base64 for JSON response if detected
            if result['fdo_detected'] and result['fdo_data']:
                result['fdo_data'] = base64.b64encode(result['fdo_data']).decode('ascii')

            return result

        except Exception as e:
            return {
                'success': False,
                'fdo_detected': False,
                'p3_frame_valid': False,
                'error': f"Base64 decoding failed: {str(e)}",
                'p3_metadata': {},
                'fdo_metadata': {},
                'fdo_data': None
            }

    @classmethod
    def quick_fdo_check(cls, frame_bytes: bytes) -> bool:
        """
        Quick check to see if P3 frame likely contains FDO data.

        Args:
            frame_bytes: P3 frame bytes

        Returns:
            True if frame likely contains FDO data
        """
        try:
            # Quick P3 validation
            if not P3FrameParser.quick_validate(frame_bytes):
                return False

            # Extract payload
            payload_data = P3FrameParser.extract_data_only(frame_bytes)
            if not payload_data or len(payload_data) < 5:  # Minimum for token + stream_id
                return False

            # Quick token check - see if first 2 bytes look like a known token
            if len(payload_data) >= 2:
                token_bytes = payload_data[:2]
                try:
                    token = token_bytes.rstrip(b'\x00').decode('ascii', errors='ignore')
                    # Accept any 2-char ASCII token (P3PayloadBuilder handles validation with fallback)
                    return len(token) == 2 and token.isprintable()
                except:
                    return False

            return False

        except Exception:
            return False

    @classmethod
    def get_detection_summary(cls, detection_result: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of detection result.

        Args:
            detection_result: Result from detect_fdo_in_p3_frame()

        Returns:
            Human-readable summary string
        """
        if not detection_result['success']:
            return f"Invalid P3 frame: {detection_result.get('error', 'Unknown error')}"

        if not detection_result['p3_frame_valid']:
            return "Invalid P3 frame format"

        if not detection_result['fdo_detected']:
            p3_type = detection_result['p3_metadata'].get('packet_type', 'Unknown')
            return f"Valid P3 {p3_type} packet, no FDO data detected"

        # FDO detected
        meta = detection_result['fdo_metadata']
        token = meta.get('token', 'Unknown')
        stream_id = meta.get('stream_id', 0)
        fdo_size = meta.get('fdo_size', 0)

        return f"FDO detected: token={token}, stream_id={stream_id}, size={fdo_size} bytes"