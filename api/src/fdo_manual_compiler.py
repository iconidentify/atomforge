"""
Manual FDO Compiler for Hex-Pair Atoms

This module implements a fast manual compiler for simple hex-data atoms,
bypassing the Wine daemon for significant performance improvements.

Binary Format (discovered through reverse engineering):
    [OPCODE][FLAGS][FORMAT_MARKER][LENGTH][...PAYLOAD...]

    - Byte 0: Opcode (atom type)
    - Byte 1: 0x0B (sub-opcode/flags, constant)
    - Byte 2: 0x80 (format marker for hex-pair data)
    - Byte 3: Payload length in bytes (1-255)
    - Bytes 4+: Direct hex pair → byte conversion

Supported atoms:
    - idb_append_data <hex_pairs>
    - dod_data <hex_pairs>
    - man_append_data <hex_pairs>
"""

import re
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FdoManualCompiler:
    """Manual compiler for FDO hex-pair atoms."""

    # Discovered opcodes (from reverse engineering)
    OPCODE_IDB_APPEND_DATA = 0x05
    OPCODE_DOD_DATA = 0x05  # Assume same as idb_append_data (to be validated)
    OPCODE_MAN_APPEND_DATA = 0x05  # Assume same (to be validated)

    # Format constants
    FLAGS = 0x0B  # Constant flags/sub-opcode
    FORMAT_MARKER = 0x80  # Marker for hex-pair format

    # Maximum payload size (conservative limit)
    MAX_PAYLOAD_LENGTH = 255

    @classmethod
    def can_compile_manually(cls, line: str) -> bool:
        """
        Check if a line can be compiled manually (hex-pair format only).

        Returns True for lines like:
            idb_append_data <01x, 02x, 03x>
            dod_data <AAx, BBx, CCx>
            man_append_data <FFx, EEx>
        """
        line_clean = line.strip()

        # Check for supported atom types
        if not any(line_clean.startswith(atom) for atom in
                   ['idb_append_data', 'dod_data', 'man_append_data']):
            return False

        # Check for hex-pair format (contains 'x' suffix on hex values)
        if not re.search(r'<[^>]*[0-9a-f]x[^>]*>', line_clean, re.IGNORECASE):
            return False

        # Extract hex pairs and validate
        hex_pairs = cls._extract_hex_pairs(line_clean)
        if not hex_pairs:
            return False

        # Check length limit
        if len(hex_pairs) > cls.MAX_PAYLOAD_LENGTH:
            logger.warning(f"Hex payload too long for manual compilation: {len(hex_pairs)} bytes")
            return False

        return True

    @classmethod
    def _extract_hex_pairs(cls, line: str) -> Optional[List[str]]:
        """
        Extract hex pairs from an atom line.

        Example:
            "idb_append_data <01x, 02x, FFx>" → ["01", "02", "FF"]
        """
        match = re.search(r'<([^>]+)>', line)
        if not match:
            return None

        content = match.group(1)

        # Extract hex values (remove 'x' suffix and whitespace)
        hex_pairs = []
        for item in content.split(','):
            item_clean = item.strip().lower()
            if item_clean.endswith('x'):
                hex_val = item_clean[:-1]  # Remove 'x'
                if re.match(r'^[0-9a-f]{1,2}$', hex_val):
                    hex_pairs.append(hex_val.zfill(2).upper())  # Normalize to 2 chars

        return hex_pairs if hex_pairs else None

    @classmethod
    def _get_atom_type(cls, line: str) -> Optional[str]:
        """Get the atom type from a line."""
        line_clean = line.strip()
        if line_clean.startswith('idb_append_data'):
            return 'idb_append_data'
        elif line_clean.startswith('dod_data'):
            return 'dod_data'
        elif line_clean.startswith('man_append_data'):
            return 'man_append_data'
        return None

    @classmethod
    def _get_opcode(cls, atom_type: str) -> int:
        """Get opcode for an atom type."""
        opcodes = {
            'idb_append_data': cls.OPCODE_IDB_APPEND_DATA,
            'dod_data': cls.OPCODE_DOD_DATA,
            'man_append_data': cls.OPCODE_MAN_APPEND_DATA,
        }
        return opcodes.get(atom_type, cls.OPCODE_IDB_APPEND_DATA)

    @classmethod
    def compile_line(cls, line: str) -> Optional[bytes]:
        """
        Manually compile a hex-pair atom line to binary.

        Args:
            line: FDO source line (e.g., "idb_append_data <01x, 02x>")

        Returns:
            Compiled binary data, or None if compilation fails
        """
        if not cls.can_compile_manually(line):
            return None

        atom_type = cls._get_atom_type(line)
        if not atom_type:
            return None

        hex_pairs = cls._extract_hex_pairs(line)
        if not hex_pairs:
            return None

        try:
            return cls._compile_hex_pairs(atom_type, hex_pairs)
        except Exception as e:
            logger.error(f"Manual compilation failed for line: {line[:50]}... Error: {e}")
            return None

    @classmethod
    def _compile_hex_pairs(cls, atom_type: str, hex_pairs: List[str]) -> bytes:
        """
        Compile hex pairs to binary format.

        Binary format:
            [OPCODE][FLAGS][FORMAT_MARKER][LENGTH][...PAYLOAD...]
        """
        opcode = cls._get_opcode(atom_type)
        payload_length = len(hex_pairs)

        if payload_length > cls.MAX_PAYLOAD_LENGTH:
            raise ValueError(f"Payload too long: {payload_length} bytes (max {cls.MAX_PAYLOAD_LENGTH})")

        # Build binary: header + payload
        binary_data = bytearray()

        # Header (4 bytes)
        binary_data.append(opcode)
        binary_data.append(cls.FLAGS)
        binary_data.append(cls.FORMAT_MARKER)
        binary_data.append(payload_length)

        # Payload (direct hex → byte conversion)
        for hex_pair in hex_pairs:
            binary_data.append(int(hex_pair, 16))

        return bytes(binary_data)

    @classmethod
    def compile_idb_append_data(cls, hex_pairs: List[str]) -> bytes:
        """Compile idb_append_data hex pairs."""
        return cls._compile_hex_pairs('idb_append_data', hex_pairs)

    @classmethod
    def compile_dod_data(cls, hex_pairs: List[str]) -> bytes:
        """Compile dod_data hex pairs."""
        return cls._compile_hex_pairs('dod_data', hex_pairs)

    @classmethod
    def compile_man_append_data(cls, hex_pairs: List[str]) -> bytes:
        """Compile man_append_data hex pairs."""
        return cls._compile_hex_pairs('man_append_data', hex_pairs)


# Validation helper (for testing)
def validate_manual_compilation(source_line: str, daemon_output: bytes) -> Tuple[bool, str]:
    """
    Validate manual compilation against daemon output.

    Args:
        source_line: Original FDO source line
        daemon_output: Binary output from fdo_daemon.exe

    Returns:
        (success, message) tuple
    """
    manual_output = FdoManualCompiler.compile_line(source_line)

    if manual_output is None:
        return False, "Manual compilation returned None"

    if manual_output == daemon_output:
        return True, "Perfect match!"

    # Detailed mismatch analysis
    manual_hex = manual_output.hex().upper()
    daemon_hex = daemon_output.hex().upper()

    if len(manual_output) != len(daemon_output):
        return False, f"Length mismatch: manual={len(manual_output)}, daemon={len(daemon_output)}"

    # Find first mismatch
    for i, (m, d) in enumerate(zip(manual_output, daemon_output)):
        if m != d:
            return False, f"Byte mismatch at offset {i}: manual=0x{m:02X}, daemon=0x{d:02X}"

    return False, "Unknown mismatch"


if __name__ == "__main__":
    # Quick test with provided example
    test_line = 'idb_append_data <01x,00x,01x,00x,01x,00x,0bx,05x,00x,00x,01x,00x,00x,00x,05x,02x,78x,00x,29x,00x,00x,00x,e7x,04x,00x,00x,24x,00x,00x,00x,00x,00x,00x,00x,00x,00x,80x,fdx,00x,00x,47x,49x,46x,38x,37x,61x,78x,00x,29x,00x,d5x,00x,00x,00x,00x,00x,ffx,00x,00x,ffx,80x,00x,ffx,80x,40x,ffx,8ex,1cx,edx,92x,24x,f7x,99x,2bx,fcx,9dx,2cx,fcx,9fx,31x,ffx,9fx,20x,fcx,a1x,34x,ffx,a2x,2fx,fcx,a4x,3cx,ffx,a4x,24x,fcx,a7x,42x,fcx,a8x,44x,ffx,aax,00x,ffx,aax,2bx,ffx,aax,39x,fcx,acx,4cx,fcx,afx,53x,fcx,b0x,56x,fcx,b3x,5bx,fdx,b6x,63x,ffx,b6x,24x,fdx,b8x,66x,fdx,bax,6ax,fdx,bex,73x,fdx,c0x,77x,fdx,c2x,7cx,fdx,c6x,84x,fdx,c7x,88x,fdx>'

    expected_hex = "050B80960100010001000B050000010000000502780029000000E70400002400000000000000000080FD000047494638376178002900D50000000000FF0000FF8000FF8040FF8E1CED9224F7992BFC9D2CFC9F31FF9F20FCA134FFA22FFCA43CFFA424FCA742FCA844FFAA00FFAA2BFFAA39FCAC4CFCAF53FCB056FCB35BFDB663FFB624FDB866FDBA6AFDBE73FDC077FDC27CFDC684FDC788FD"

    result = FdoManualCompiler.compile_line(test_line)

    if result:
        result_hex = result.hex().upper()
        print(f"Manual compilation result:")
        print(f"  Expected: {expected_hex}")
        print(f"  Got:      {result_hex}")
        print(f"  Match: {result_hex == expected_hex}")
    else:
        print("Manual compilation failed!")
