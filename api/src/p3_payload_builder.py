#!/usr/bin/env python3
"""
P3 Payload Builder
Assembles P3 protocol payloads with proper token and stream_id headers
Based on reverse engineering of AOLBUF.AOL protocol implementation
"""

import struct
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class P3PayloadBuilder:
    """
    Builder for P3 protocol payloads.
    Handles token and stream_id header assembly according to AOL protocol specs.
    """

    # Token types and their stream_id byte lengths (from AOLBUF reverse engineering)
    TOKEN_STREAM_ID_SIZES = {
        'AT': 2,   # Standard atom token - corrected for proper DOD/AT packet structure
        'at': 4,   # Extended atom token
        'At': 3,   # Extended atom token (case variant) - corrected based on user feedback
        'f1': 2,   # Form request
        'ff': 2,   # Form control
        'DD': 2,   # Data direct
        'Dd': 2,   # Data direct (case variant) - nested within ZD wrapper
        'D3': 2,   # Special data
        'NX': 2,   # NX token with 2-byte stream ID
        'OT': 2,   # Alert message
        'XS': 2,   # Force off
        'Aa': 2,   # AOL frame type - extracted from reverse engineering examples
        'aS': 2,   # AOL frame type - extracted from reverse engineering examples
        'iO': 2,   # AOL frame type - extracted from reverse engineering examples
        'ME': 2,   # AOL frame type - extracted from reverse engineering examples
        'fh': 2,   # AOL frame type with 2-byte stream ID
        'iS': 2,   # AOL frame type with 2-byte stream ID - extracted from protocol analysis
        'CA': 2,   # CA frame type with 2-byte stream ID (little-endian)
    }

    # Protocol limits from AOLBUF
    MAX_SEGMENT_SIZE = 0xFF        # 255 bytes - hard limit
    MAX_OUTBOUND_SIZE = 119        # Per-packet limit for client->host
    CONTINUATION_MARKER = 0x80     # Marker for segmented atoms

    @classmethod
    def build_packet(cls, data: bytes, stream_id: int, token: str) -> bytes:
        """
        Build P3 payload with token and stream_id header.

        Args:
            data: Compiled atom data to include in payload
            stream_id: Stream identifier (varies by token)
            token: 2-byte token identifying packet type

        Returns:
            Complete P3 payload bytes ready for P3 protocol wrapper

        Raises:
            ValueError: If token is invalid or stream_id is out of range
        """
        if token not in cls.TOKEN_STREAM_ID_SIZES:
            raise ValueError(f"Invalid token '{token}'. Valid tokens: {list(cls.TOKEN_STREAM_ID_SIZES.keys())}")

        stream_id_size = cls.TOKEN_STREAM_ID_SIZES[token]

        # Validate stream_id fits in allocated bytes
        max_stream_id = (1 << (stream_id_size * 8)) - 1
        if stream_id < 0 or stream_id > max_stream_id:
            raise ValueError(f"stream_id {stream_id} out of range for token '{token}' (max: {max_stream_id})")

        packet = bytearray()

        # Token is always 2 bytes, ASCII-encoded
        token_bytes = token.encode('ascii')[:2].ljust(2, b'\x00')
        packet.extend(token_bytes)

        # Stream ID size varies by token type, little-endian
        stream_id_bytes = stream_id.to_bytes(stream_id_size, 'little')
        packet.extend(stream_id_bytes)

        # Append the atom data
        packet.extend(data)

        logger.debug(f"Built P3 packet: token={token}, stream_id={stream_id}, data_size={len(data)}, total_size={len(packet)}")
        return bytes(packet)

    @classmethod
    def get_header_size(cls, token: str) -> int:
        """
        Get the header size for a given token.

        Args:
            token: Token type

        Returns:
            Header size in bytes (token + stream_id)
        """
        if token not in cls.TOKEN_STREAM_ID_SIZES:
            raise ValueError(f"Invalid token '{token}'")

        return 2 + cls.TOKEN_STREAM_ID_SIZES[token]

    @classmethod
    def segment_data_if_needed(cls, data: bytes) -> list[bytes]:
        """
        Split data exceeding 255 bytes with continuation markers.
        Matches AOLBUF's segmentation logic from reverse engineering.

        Args:
            data: Raw compiled atom data

        Returns:
            List of segments with continuation markers as needed
        """
        if len(data) <= cls.MAX_SEGMENT_SIZE:
            return [data]

        segments = []
        offset = 0

        # First segment - no continuation marker, full 255 bytes
        first_chunk = data[:cls.MAX_SEGMENT_SIZE]
        segments.append(first_chunk)
        offset = cls.MAX_SEGMENT_SIZE

        # Subsequent segments with continuation markers
        while offset < len(data):
            # Reserve 1 byte for continuation marker
            remaining = len(data) - offset
            chunk_size = min(cls.MAX_SEGMENT_SIZE - 1, remaining)

            # Build segment with continuation marker (0x80 | length)
            segment = bytearray()
            segment.append(cls.CONTINUATION_MARKER | chunk_size)
            segment.extend(data[offset:offset + chunk_size])

            segments.append(bytes(segment))
            offset += chunk_size

        logger.debug(f"Segmented {len(data)} bytes into {len(segments)} segments")
        return segments

    @classmethod
    def calculate_packet_overhead(cls, token: str) -> int:
        """
        Calculate the overhead (header size) for packets with given token.

        Args:
            token: Token type

        Returns:
            Overhead bytes per packet
        """
        return cls.get_header_size(token)

    @classmethod
    def validate_packet_size(cls, data_size: int, token: str) -> Dict[str, Any]:
        """
        Validate if data fits within protocol limits for given token.

        Args:
            data_size: Size of data to be packeted
            token: Token type

        Returns:
            Validation result with details
        """
        header_size = cls.get_header_size(token)
        total_size = header_size + data_size

        result = {
            'valid': True,
            'warnings': [],
            'info': {
                'data_size': data_size,
                'header_size': header_size,
                'total_size': total_size,
                'max_outbound': cls.MAX_OUTBOUND_SIZE
            }
        }

        if total_size > cls.MAX_OUTBOUND_SIZE:
            result['warnings'].append(
                f"Packet size {total_size} exceeds outbound limit {cls.MAX_OUTBOUND_SIZE}"
            )

        if data_size > cls.MAX_SEGMENT_SIZE:
            result['warnings'].append(
                f"Data size {data_size} exceeds segment limit {cls.MAX_SEGMENT_SIZE}, will require segmentation"
            )

        return result

    @classmethod
    def parse_packet_header(cls, packet: bytes) -> Dict[str, Any]:
        """
        Parse P3 packet header to extract token and stream_id.

        Args:
            packet: P3 payload bytes

        Returns:
            Header information dict

        Raises:
            ValueError: If packet is too short or has invalid header
        """
        if len(packet) < 2:
            raise ValueError("Packet too short for token")

        # Extract token (2 bytes)
        token_bytes = packet[:2]
        token = token_bytes.rstrip(b'\x00').decode('ascii', errors='ignore')

        if token not in cls.TOKEN_STREAM_ID_SIZES:
            raise ValueError(f"Unknown token '{token}' in packet header")

        stream_id_size = cls.TOKEN_STREAM_ID_SIZES[token]
        header_size = 2 + stream_id_size

        if len(packet) < header_size:
            raise ValueError(f"Packet too short for token '{token}' (needs {header_size} bytes)")

        # Extract stream_id
        stream_id_bytes = packet[2:header_size]
        stream_id = int.from_bytes(stream_id_bytes, 'little')

        # Extract data
        data = packet[header_size:] if len(packet) > header_size else b''

        return {
            'token': token,
            'stream_id': stream_id,
            'header_size': header_size,
            'data_size': len(data),
            'data': data
        }

    @classmethod
    def estimate_chunk_count(cls, total_data_size: int, token: str) -> int:
        """
        Estimate how many P3 packets will be needed for given data size.

        Args:
            total_data_size: Total bytes of compiled data
            token: Token type

        Returns:
            Estimated number of packets needed
        """
        header_size = cls.get_header_size(token)
        effective_payload_size = cls.MAX_OUTBOUND_SIZE - header_size

        if effective_payload_size <= 0:
            return 0

        return (total_data_size + effective_payload_size - 1) // effective_payload_size