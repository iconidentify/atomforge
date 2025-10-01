#!/usr/bin/env python3
"""
P3 Frame Parser
Fast P3 protocol frame parser for extracting payload data without CRC validation.
Based on P3 protocol specification for AOL client compatibility.
"""

import struct
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class P3FrameParseError(Exception):
    """Errors specific to P3 frame parsing operations"""
    pass

class P3FrameParser:
    """
    Fast P3 frame parser optimized for FDO auto-detection.
    Skips CRC validation for performance in real-time hint systems.
    """

    # P3 protocol constants
    SYNC_BYTE = 0x5A
    MSG_END_BYTE = 0x0D
    MIN_FRAME_SIZE = 9  # sync + crc + length + tx_seq + rx_seq + type + msg_end (minimum)

    # Packet type constants
    PACKET_TYPES = {
        0x20: 'DATA',
        0x21: 'SS',
        0x22: 'SSR',
        0x23: 'INIT',
        0x24: 'ACK',
        0x25: 'NAK',
        0x26: 'HEARTBEAT'
    }

    @classmethod
    def parse_frame(cls, frame_bytes: bytes) -> Dict[str, Any]:
        """
        Parse P3 frame and extract payload data.

        P3 Frame Structure (big-endian):
        Offset  Length  Type    Field
        0x00    0x01    uint8   sync (0x5A)
        0x01    0x02    uint16  crc (ignored)
        0x03    0x02    uint16  length
        0x05    0x01    uint8   tx_seq
        0x06    0x01    uint8   rx_seq
        0x07    0x01    uint8   type
        0x08    varies  bytes   data
        last    0x01    uint8   msg_end (0x0D)

        Args:
            frame_bytes: Complete P3 frame bytes

        Returns:
            Parsed frame data with payload extracted

        Raises:
            P3FrameParseError: If frame is malformed or invalid
        """
        if not frame_bytes:
            raise P3FrameParseError("Empty frame data")

        if len(frame_bytes) < cls.MIN_FRAME_SIZE:
            raise P3FrameParseError(f"Frame too short: {len(frame_bytes)} bytes (minimum: {cls.MIN_FRAME_SIZE})")

        try:
            # Parse sync byte
            sync = frame_bytes[0]
            if sync != cls.SYNC_BYTE:
                raise P3FrameParseError(f"Invalid sync byte: 0x{sync:02X} (expected: 0x{cls.SYNC_BYTE:02X})")

            # Skip CRC field (bytes 1-2) - not validated per user requirements
            crc = struct.unpack('>H', frame_bytes[1:3])[0]

            # Parse length field (big-endian)
            length = struct.unpack('>H', frame_bytes[3:5])[0]
            if length < 3:
                raise P3FrameParseError(f"Invalid length field: {length} (minimum: 3)")

            # Parse sequence and type fields
            tx_seq = frame_bytes[5]
            rx_seq = frame_bytes[6]
            type_field = frame_bytes[7]

            # Remove client bit (high bit) to get actual packet type
            packet_type_value = type_field & 0x7F
            packet_type = cls.PACKET_TYPES.get(packet_type_value, f"UNKNOWN(0x{packet_type_value:02X})")

            # Calculate data field boundaries
            data_length = length - 3  # Subtract tx_seq, rx_seq, type bytes
            data_start = 8
            data_end = data_start + data_length

            # Validate frame has enough bytes for claimed data length
            expected_frame_size = data_end + 1  # +1 for msg_end byte
            if len(frame_bytes) < expected_frame_size:
                raise P3FrameParseError(
                    f"Frame size mismatch: got {len(frame_bytes)} bytes, expected {expected_frame_size} "
                    f"(length field claims {data_length} data bytes)"
                )

            # Extract data field
            data = frame_bytes[data_start:data_end]

            # Validate msg_end byte
            msg_end = frame_bytes[data_end]
            if msg_end != cls.MSG_END_BYTE:
                raise P3FrameParseError(f"Invalid msg_end byte: 0x{msg_end:02X} (expected: 0x{cls.MSG_END_BYTE:02X})")

            logger.debug(f"Parsed P3 frame: type={packet_type}, data_length={data_length}, tx_seq={tx_seq}, rx_seq={rx_seq}")

            return {
                'success': True,
                'sync': sync,
                'crc': crc,  # Included but not validated
                'length': length,
                'tx_seq': tx_seq,
                'rx_seq': rx_seq,
                'type_field': type_field,
                'packet_type': packet_type,
                'packet_type_value': packet_type_value,
                'client_packet': bool(type_field & 0x80),  # High bit indicates client packet
                'data': data,
                'data_length': data_length,
                'msg_end': msg_end,
                'frame_size': len(frame_bytes)
            }

        except struct.error as e:
            raise P3FrameParseError(f"Struct unpacking error: {e}")
        except IndexError as e:
            raise P3FrameParseError(f"Frame truncated: {e}")

    @classmethod
    def quick_validate(cls, frame_bytes: bytes) -> bool:
        """
        Quick validation to check if bytes look like a P3 frame.

        Args:
            frame_bytes: Bytes to validate

        Returns:
            True if bytes appear to be a valid P3 frame
        """
        if not frame_bytes or len(frame_bytes) < cls.MIN_FRAME_SIZE:
            return False

        # Check sync byte
        if frame_bytes[0] != cls.SYNC_BYTE:
            return False

        try:
            # Check length field consistency
            length = struct.unpack('>H', frame_bytes[3:5])[0]
            if length < 3:
                return False

            # Check if frame has claimed size
            expected_size = 8 + (length - 3) + 1  # header + data + msg_end
            if len(frame_bytes) != expected_size:
                return False

            # Check msg_end byte
            if frame_bytes[-1] != cls.MSG_END_BYTE:
                return False

            return True

        except (struct.error, IndexError):
            return False

    @classmethod
    def extract_data_only(cls, frame_bytes: bytes) -> Optional[bytes]:
        """
        Fast extraction of just the data field from a P3 frame.

        Args:
            frame_bytes: P3 frame bytes

        Returns:
            Data field bytes, or None if extraction fails
        """
        try:
            parsed = cls.parse_frame(frame_bytes)
            return parsed['data']
        except P3FrameParseError:
            return None