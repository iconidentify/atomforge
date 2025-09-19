#!/usr/bin/env python3
"""
AOL P3 Packet Extraction Module - Enhanced Version
Extracts FDO data from AOL P3 packet streams for clean decompilation
Upgraded with CRC validation, streaming support, and robust error handling
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Callable
import re

# ----------------------------
# Utilities & protocol helpers
# ----------------------------

def _is_printable_token_byte(b: int) -> bool:
    # Token bytes are typically ASCII letters/digits; allow A–Z, a–z, 0–9
    return (0x30 <= b <= 0x39) or (0x41 <= b <= 0x5A) or (0x61 <= b <= 0x7A)

def _crc16_ibm_arc(data: bytes) -> int:
    # CRC-16/IBM (aka ARC), init=0x0000, poly=0xA001, reflected
    crc = 0
    for ch in data:
        crc ^= ch
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            crc &= 0xFFFF
    return crc

def _verify_crc16_p3(packet: bytes) -> bool:
    """
    Classic P3 CRC rule: bytes[1:3] hold CRC(H,L).
    Compute CRC over the packet with the first 5 bytes removed.
    (Newer variants may put b'**' instead and skip CRC entirely.)
    """
    if len(packet) < 6:
        return False
    hdr = packet[:10] if len(packet) >= 10 else packet
    if hdr[1:3] == b'**':
        return True
    stored = (packet[1] << 8) | packet[2]
    computed = _crc16_ibm_arc(packet[5:])
    return stored == computed

def _strip_optional_len_prefix(payload: bytes, max_layers: int = 2) -> Tuple[bytes, List[str]]:
    """
    Strip up to `max_layers` little-endian DWORD length prefixes that may wrap
    the atom stream (BUF layer). Each removal is logged in notes.
    Heuristic:
      - Need >= 6 bytes (len dword + stream-id)
      - L = little-endian dword at [0:4]
      - 0 < L <= len(payload) - 4
      - Next two bytes plausibly look like a stream-id (smallish is ok)
    """
    notes: List[str] = []
    p = payload
    layers = 0
    while layers < max_layers and len(p) >= 6:
        L = int.from_bytes(p[:4], "little", signed=False)
        if 0 < L <= (len(p) - 4):
            sid_lo, sid_hi = p[4], p[5]
            # stream-ids in captured traffic are usually small (heuristic)
            if sid_lo <= 0x7F and sid_hi <= 0x7F:
                notes.append(f"Stripped LEN prefix 0x{L:08x} before stream-id {sid_hi:02x}{sid_lo:02x}.")
                p = p[4:]
                layers += 1
                continue
        break
    return p, notes

def _looks_plausible_token(hdr: bytes) -> bool:
    return _is_printable_token_byte(hdr[8]) and _is_printable_token_byte(hdr[9])

def _printable_ratio(b: bytes) -> float:
    if not b:
        return 1.0
    printable = sum(1 for x in b if 32 <= x <= 126 or x in (9, 10, 13))
    return printable / len(b)

def _classify_fdo_candidate(
    token: str,
    payload_raw: bytes,
    strip_fn: Callable[[bytes], Tuple[bytes, List[str]]],
    token_allow: Optional[set] = None,
) -> Tuple[bool, bytes, List[str]]:
    """
    Decide whether this payload likely contains compressed FDO.
    Returns (is_fdo, fdo_bytes, notes). fdo_bytes starts at stream-id if True.
    """
    notes: List[str] = []
    if token_allow is None:
        token_allow = {"AT", "at"}

    # Token gate
    if token not in token_allow:
        notes.append(f"token '{token}' not in allow-list; skipping as non-FDO")
        return False, b"", notes

    # Minimum raw size
    if len(payload_raw) < 6:
        notes.append("payload too small (<6) for FDO; skipping")
        return False, b"", notes

    # Strip optional BUF length prefix
    fdo_bytes, strip_notes = strip_fn(payload_raw)
    notes.extend(strip_notes)

    # Need at least stream-id (2) + some body (>=2)
    if len(fdo_bytes) < 4:
        notes.append("after strip, too small (<4) to hold stream-id+body; skipping")
        return False, b"", notes

    # Stream-id sanity (little-endian)
    sid = fdo_bytes[0] | (fdo_bytes[1] << 8)
    if not (0x0001 <= sid <= 0x7FFF):
        notes.append(f"implausible stream-id 0x{sid:04X}; skipping")
        return False, b"", notes

    # Anti-plain-text: compressed FDO shouldn’t look like plain ASCII
    body = fdo_bytes[2:]
    if _printable_ratio(body) >= 0.80:
        notes.append("payload body looks like plain ASCII (>=80% printable); skipping")
        return False, b"", notes

    notes.append(f"accepted as FDO: stream-id=0x{sid:04X}, len={len(fdo_bytes)}")
    return True, fdo_bytes, notes

# ----------------------------
# Output model
# ----------------------------

@dataclass
class P3Header:
    z: int                   # 0x5A
    crc_hi: int
    crc_lo: int
    null_00: int             # should be 0x00
    byte4: int               # "length-ish" (not reliable; informational only)
    counter6: int            # seq/heartbeat (heuristic)
    counter7: int            # seq/heartbeat (heuristic)
    space_20: int            # should be 0x20
    token: str               # 2 ASCII chars

@dataclass
class P3Frame:
    # Absolute offsets are w.r.t. the stream processed by the extractor
    start_offset: int
    end_offset: int
    header: P3Header
    raw_packet: bytes                 # [start .. CR] inclusive of CR
    payload_raw: bytes                # between header and CR
    fdo_bytes: bytes                  # payload after wrapper-stripping
    crc_checked: bool
    crc_ok: Optional[bool]
    notes: List[str] = field(default_factory=list)

# ----------------------------
# Extractor (streaming capable)
# ----------------------------

class P3FDOExtractor:
    """
    Robust P3 -> FDO extractor.

    Protocol assumptions (from AOL P3 notes):
      • Byte 0 == 0x5A ('Z')
      • Bytes 1–2 = CRC16(H,L) for classic clients; newer may be b'**'
      • Byte 3 == 0x00
      • Byte 7 == 0x20 (' ')
      • Bytes 8–9: ASCII token (two letters) indicating packet type
      • Remainder is compressed FDO or data string; packet ends with 0x0D (CR)
    See notes: first-ten-bytes layout and token position.
    """

    def __init__(
        self,
        strict_crc: bool = False,
        max_len_prefix_layers: int = 2,
        max_scan_ahead: int = 2_000_000,
        fdo_token_allow: Optional[set] = None,
    ):
        self.strict_crc = strict_crc
        self.max_layers = max_len_prefix_layers
        self.max_scan_ahead = max_scan_ahead
        self.fdo_token_allow = fdo_token_allow or {"AT", "at"}
        self._buf = bytearray()
        self._base_offset = 0  # how many bytes we've discarded before current buffer

    def feed(self, chunk: bytes) -> List[P3Frame]:
        """Feed bytes; returns any fully parsed frames."""
        self._buf.extend(chunk)
        frames: List[P3Frame] = []
        Z, CR = 0x5A, 0x0D
        i = 0

        while True:
            # 1) Find next 'Z'
            try:
                start = self._buf.index(Z, i)
            except ValueError:
                # No start marker left; drop prefix noise to keep memory bounded
                if len(self._buf) > 1_000_000:
                    self._base_offset += start if 'start' in locals() else len(self._buf)
                    self._buf.clear()
                break

            # Ensure we have at least a header
            if start + 10 > len(self._buf):
                # Need more data
                break

            hdr = self._buf[start:start + 10]
            notes: List[str] = []

            # 2) Header invariants (fast reject)
            if hdr[3] != 0x00 or hdr[7] != 0x20:
                i = start + 1
                continue
            if not _looks_plausible_token(hdr):
                i = start + 1
                continue

            # 3) Find CR terminator for this packet
            # For AOL packets, try multiple CR positions in case of embedded CRs
            potential_ends = []
            search_pos = start + 10
            while search_pos < len(self._buf):
                try:
                    cr_pos = self._buf.index(CR, search_pos)
                    if (cr_pos - start) <= self.max_scan_ahead:  # Sanity cap
                        potential_ends.append(cr_pos)
                    search_pos = cr_pos + 1
                except ValueError:
                    break

            if not potential_ends:
                # No CR found; wait for more data
                break

            # Try each potential end position, preferring ones that validate properly
            best_end = None
            best_score = -1
            
            # Check if there's another Z marker after this one (helps identify packet boundary)
            next_z_pos = None
            try:
                next_z_pos = self._buf.index(Z, start + 1)
            except ValueError:
                pass

            for end in potential_ends:
                packet_candidate = bytes(self._buf[start:end + 1])
                payload_candidate = packet_candidate[10:-1]  # exclude header and CR

                # Score this candidate based on multiple factors
                score = 0
                
                # Factor 1: If this CR is immediately before the next Z, it's very likely the correct boundary
                if next_z_pos is not None and end == next_z_pos - 1:
                    score = 2000  # Highest priority - CR right before next packet
                
                # Factor 2: Length prefix validation
                if len(payload_candidate) >= 6:
                    L = int.from_bytes(payload_candidate[:4], "little", signed=False)
                    if 0 < L <= (len(payload_candidate) - 4):
                        sid_lo, sid_hi = payload_candidate[4], payload_candidate[5]
                        if sid_lo <= 0x7F and sid_hi <= 0x7F:
                            # Check if length matches exactly (strong indicator of correct boundary)
                            if L == len(payload_candidate) - 4:
                                score += 1000  # Exact length match
                            else:
                                score += 100  # Length valid but not exact
                        else:
                            score += 50   # Moderate preference
                    else:
                        score += 10   # Weak preference - length doesn't validate but still possible

                # For equal scores, prefer shorter/earlier packets (P3 packets are typically small)
                # But use a very small penalty so exact length matches always win
                score -= (end - start) / 100000.0

                if score > best_score:
                    best_score = score
                    best_end = end

            if best_end is None:
                # Fall back to first CR if no good candidate
                best_end = potential_ends[0]

            end = best_end

            packet = bytes(self._buf[start:end + 1])
            token = bytes((hdr[8], hdr[9])).decode("ascii", errors="replace")

            # 4) CRC (optional strictness) - configured for AOL 4 compatibility
            crc_ok: Optional[bool] = None
            crc_checked = False
            if self.strict_crc or hdr[1:3] != b'**':
                crc_checked = True
                crc_ok = _verify_crc16_p3(packet)
                if self.strict_crc and not crc_ok:
                    notes.append("CRC failed in strict mode – packet dropped.")
                    i = start + 1
                    continue
                if not self.strict_crc and crc_ok is False:
                    notes.append("CRC failed (non-strict): keeping packet but marking crc_ok=False.")

            # 5) Payload & FDO classification (only keep likely-FDO)
            payload = packet[10:-1]  # between header and CR (exclude CR at end)
            is_fdo, fdo, classify_notes = _classify_fdo_candidate(
                token=token,
                payload_raw=payload,
                strip_fn=lambda p: _strip_optional_len_prefix(p, self.max_layers),
                token_allow=self.fdo_token_allow,
            )
            notes.extend(classify_notes)

            if not is_fdo:
                # Not FDO; advance and continue WITHOUT appending a frame
                i = end + 1
                continue

            # 6) Build frame
            header = P3Header(
                z=hdr[0],
                crc_hi=hdr[1],
                crc_lo=hdr[2],
                null_00=hdr[3],
                byte4=hdr[4],
                counter6=hdr[5],
                counter7=hdr[6],
                space_20=hdr[7],
                token=token,
            )
            frames.append(P3Frame(
                start_offset=self._base_offset + start,
                end_offset=self._base_offset + end,
                header=header,
                raw_packet=packet,
                payload_raw=payload,
                fdo_bytes=fdo,
                crc_checked=crc_checked,
                crc_ok=crc_ok,
                notes=notes
            ))

            # 7) Advance cursor to scan for next frame
            i = end + 1

            # 8) Drop consumed prefix to keep buffer small
            #    (Only when we've advanced far enough.)
            if i > 65536:
                self._base_offset += i
                del self._buf[:i]
                i = 0

        return frames

    def flush(self) -> List[P3Frame]:
        """
        Call when the stream ends. Tries to parse any trailing complete frame,
        then clears internal buffers. Returns any final frames.
        """
        frames = self.feed(b"")  # one last pass
        # Drop any unconsumed bytes (incomplete frame) but preserve accounting
        self._base_offset += len(self._buf)
        self._buf.clear()
        return frames

# ----------------------------
# Convenience one-shot API
# ----------------------------

def extract_p3_fdo(data: bytes, strict_crc: bool = False) -> List[P3Frame]:
    """
    One-shot convenience wrapper around P3FDOExtractor for non-streaming inputs.
    Defaults to non-strict CRC mode for AOL 4 compatibility.
    """
    ex = P3FDOExtractor(strict_crc=strict_crc)
    frames = ex.feed(data)
    # Don't call flush() since feed() already processed all the data
    # flush() is only needed for streaming scenarios where you want to finalize
    return frames

# ----------------------------
# Legacy API compatibility layer
# ----------------------------

def extract_p3_frames_with_fdo(buf: bytes) -> List[Dict[str, Any]]:
    """
    Legacy compatibility function that maintains the original API.
    Converts new P3Frame objects back to the original dictionary format.
    """
    frames = extract_p3_fdo(buf, strict_crc=False)  # AOL 4 compatible

    # Convert to legacy format
    legacy_frames = []
    for frame in frames:
        legacy_frame = {
            "offset": frame.start_offset,
            "length": len(frame.raw_packet),
            "token": frame.header.token,
            "counter6": frame.header.counter6,
            "counter7": frame.header.counter7,
            "crc_bytes": f"{frame.header.crc_hi:02x}{frame.header.crc_lo:02x}",
            "payload_raw": frame.payload_raw,
            "fdo_bytes": frame.fdo_bytes,
        }
        legacy_frames.append(legacy_frame)

    return legacy_frames

# ----------------------------
# High-level P3 packet processor
# ----------------------------

class P3Extractor:
    """High-level P3 packet processor for FDO extraction with enhanced capabilities"""

    def __init__(self, strict_crc: bool = False):
        """Initialize with AOL 4 compatibility by default (strict_crc=False)"""
        self.strict_crc = strict_crc

    def hex_string_to_bytes(self, hex_string: str) -> bytes:
        """Convert hex string to bytes, handling various formats"""
        # Remove whitespace, colons, and other common separators
        clean_hex = re.sub(r'[^0-9A-Fa-f]', '', hex_string.strip())

        if len(clean_hex) % 2 != 0:
            raise ValueError("Hex string must have even length")

        if not clean_hex:
            raise ValueError("Empty hex string")

        try:
            return bytes.fromhex(clean_hex)
        except ValueError as e:
            raise ValueError(f"Invalid hex string: {e}")

    def bytes_to_hex_string(self, data: bytes) -> str:
        """Convert bytes to clean hex string (uppercase, no spaces)"""
        return data.hex().upper()

    def extract_fdo_from_hex(self, hex_string: str) -> Dict[str, Any]:
        """
        Extract FDO data from hex string containing P3 packets
        Enhanced with better error reporting and AOL 4 compatibility

        Returns:
            {
                'success': bool,
                'fdo_hex': str,           # concatenated FDO data as hex
                'frames_found': int,      # number of P3 frames processed
                'total_fdo_bytes': int,   # total FDO bytes extracted
                'error': str,             # error message if success=False
                'frames_with_crc_issues': int,  # count of frames with CRC problems
                'processing_notes': List[str]   # detailed processing information
            }
        """
        try:
            # Convert hex string to bytes
            packet_data = self.hex_string_to_bytes(hex_string)

            # Extract P3 frames using enhanced extractor
            frames = extract_p3_fdo(packet_data, strict_crc=self.strict_crc)

            if not frames:
                return {
                    'success': False,
                    'fdo_hex': '',
                    'frames_found': 0,
                    'total_fdo_bytes': 0,
                    'frames_with_crc_issues': 0,
                    'processing_notes': [],
                    'error': 'No P3 packets found in hex data'
                }

            # Concatenate all FDO bytes from frames
            all_fdo_bytes = b''
            frames_with_crc_issues = 0
            all_notes = []

            for frame in frames:
                fdo_bytes = frame.fdo_bytes
                if fdo_bytes:
                    all_fdo_bytes += fdo_bytes

                # Track CRC issues for reporting
                if frame.crc_checked and frame.crc_ok is False:
                    frames_with_crc_issues += 1

                # Collect processing notes
                all_notes.extend(frame.notes)

            if not all_fdo_bytes:
                return {
                    'success': False,
                    'fdo_hex': '',
                    'frames_found': len(frames),
                    'total_fdo_bytes': 0,
                    'frames_with_crc_issues': frames_with_crc_issues,
                    'processing_notes': all_notes,
                    'error': f'Found {len(frames)} P3 packets but no FDO data extracted'
                }

            # Convert back to hex string
            fdo_hex = self.bytes_to_hex_string(all_fdo_bytes)

            return {
                'success': True,
                'fdo_hex': fdo_hex,
                'frames_found': len(frames),
                'total_fdo_bytes': len(all_fdo_bytes),
                'frames_with_crc_issues': frames_with_crc_issues,
                'processing_notes': all_notes,
                'error': None
            }

        except ValueError as e:
            return {
                'success': False,
                'fdo_hex': '',
                'frames_found': 0,
                'total_fdo_bytes': 0,
                'frames_with_crc_issues': 0,
                'processing_notes': [],
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'fdo_hex': '',
                'frames_found': 0,
                'total_fdo_bytes': 0,
                'frames_with_crc_issues': 0,
                'processing_notes': [],
                'error': f'Unexpected error during P3 extraction: {str(e)}'
            }

    def get_frame_details(self, hex_string: str) -> List[Dict[str, Any]]:
        """
        Get detailed information about P3 frames for debugging/analysis
        Enhanced with CRC validation results and processing notes

        Returns list of frame details with additional formatting
        """
        try:
            packet_data = self.hex_string_to_bytes(hex_string)
            frames = extract_p3_fdo(packet_data, strict_crc=self.strict_crc)

            # Add formatted details for each frame
            detailed_frames = []
            for frame in frames:
                detailed_frame = {
                    # Original fields for backward compatibility
                    'offset': frame.start_offset,
                    'length': len(frame.raw_packet),
                    'token': frame.header.token,
                    'counter6': frame.header.counter6,
                    'counter7': frame.header.counter7,
                    'crc_bytes': f"{frame.header.crc_hi:02x}{frame.header.crc_lo:02x}",
                    'payload_raw': frame.payload_raw,
                    'fdo_bytes': frame.fdo_bytes,

                    # Enhanced fields
                    'payload_raw_hex': frame.payload_raw.hex().upper(),
                    'fdo_bytes_hex': frame.fdo_bytes.hex().upper(),
                    'payload_raw_size': len(frame.payload_raw),
                    'fdo_bytes_size': len(frame.fdo_bytes),
                    'crc_checked': frame.crc_checked,
                    'crc_ok': frame.crc_ok,
                    'processing_notes': frame.notes,

                    # Compression info
                    'prefix_stripped_bytes': len(frame.payload_raw) - len(frame.fdo_bytes) if len(frame.payload_raw) > len(frame.fdo_bytes) else 0
                }

                detailed_frames.append(detailed_frame)

            return detailed_frames

        except Exception as e:
            return []

# Global extractor instance with AOL 4 compatibility
_extractor = None

def get_extractor() -> P3Extractor:
    """Get the global P3 extractor instance configured for AOL 4 compatibility"""
    global _extractor
    if _extractor is None:
        _extractor = P3Extractor(strict_crc=False)  # AOL 4 compatible
    return _extractor

# Convenience functions
def extract_fdo_from_hex(hex_string: str) -> Dict[str, Any]:
    """Extract FDO data from hex string containing P3 packets"""
    return get_extractor().extract_fdo_from_hex(hex_string)

def get_p3_frame_details(hex_string: str) -> List[Dict[str, Any]]:
    """Get detailed P3 frame information for analysis"""
    return get_extractor().get_frame_details(hex_string)