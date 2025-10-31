#!/usr/bin/env python3
"""
Test script for hex-pair support in idb_append_data and dod_data
"""

import sys
sys.path.insert(0, '/Users/chrisk/Documents/aol_lfg/source/atomforge/api/src')

from fdo_atom_parser import FdoAtomParser

def test_idb_append_data_hex_pairs():
    """Test that long hex-pair idb_append_data lines are split correctly."""
    print("=" * 80)
    print("TEST: idb_append_data hex-pair splitting")
    print("=" * 80)

    # Create a test case with 250 hex pairs (should be split into 2 chunks of 200 + 50)
    hex_pairs = ', '.join([f'{i:02X}x' for i in range(250)])
    test_line = f"      idb_append_data <{hex_pairs}>"

    print(f"\nOriginal line length: {len(test_line)} characters")
    print(f"Number of hex pairs: 250")
    print(f"Expected: Split into 2 lines (200 pairs + 50 pairs)")
    print(f"Max pairs per line: {FdoAtomParser.MAX_IDB_APPEND_DATA_HEX_PAIRS}")

    # Test detection
    is_long = FdoAtomParser._is_long_idb_append_data_hex(test_line)
    print(f"\n_is_long_idb_append_data_hex() result: {is_long}")

    if not is_long:
        print("ERROR: Failed to detect long hex-pair format!")
        return False

    # Test splitting
    split_lines = FdoAtomParser._split_idb_append_data_hex_line(test_line)
    print(f"\nActual: Split into {len(split_lines)} lines")

    for i, line in enumerate(split_lines):
        pairs = [p.strip() for p in FdoAtomParser._extract_hex_pairs_from_idb_append_data(line).split(',') if p.strip()]
        print(f"  Line {i+1}: {len(pairs)} pairs")

    # Verify results
    if len(split_lines) != 2:
        print(f"\nERROR: Expected 2 lines, got {len(split_lines)}")
        return False

    print("\nSUCCESS: idb_append_data hex-pair splitting works!")
    return True

def test_dod_data_hex_pairs():
    """Test that long hex-pair dod_data lines are split correctly."""
    print("\n" + "=" * 80)
    print("TEST: dod_data hex-pair splitting")
    print("=" * 80)

    # Create a test case with 250 hex pairs (should be split into 2 chunks of 200 + 50)
    hex_pairs = ', '.join([f'{i:02X}x' for i in range(250)])
    test_line = f"      dod_data <{hex_pairs}>"

    print(f"\nOriginal line length: {len(test_line)} characters")
    print(f"Number of hex pairs: 250")
    print(f"Expected: Split into 2 lines (200 pairs + 50 pairs)")
    print(f"Max pairs per line: {FdoAtomParser.MAX_DOD_DATA_HEX_PAIRS}")

    # Test detection
    is_long = FdoAtomParser._is_long_dod_data_hex(test_line)
    print(f"\n_is_long_dod_data_hex() result: {is_long}")

    if not is_long:
        print("ERROR: Failed to detect long hex-pair format!")
        return False

    # Test splitting
    split_lines = FdoAtomParser._split_dod_data_hex_line(test_line)
    print(f"\nActual: Split into {len(split_lines)} lines")

    for i, line in enumerate(split_lines):
        pairs = [p.strip() for p in FdoAtomParser._extract_hex_pairs_from_dod_data(line).split(',') if p.strip()]
        print(f"  Line {i+1}: {len(pairs)} pairs")

    # Verify results
    if len(split_lines) != 2:
        print(f"\nERROR: Expected 2 lines, got {len(split_lines)}")
        return False

    print("\nSUCCESS: dod_data hex-pair splitting works!")
    return True

def test_full_preprocessing():
    """Test full preprocessing with all atom types."""
    print("\n" + "=" * 80)
    print("TEST: Full preprocessing with all atom types")
    print("=" * 80)

    # Create hex pairs for each atom type
    man_hex_pairs = ', '.join([f'{i:02X}x' for i in range(200)])  # Over 150 limit
    idb_hex_pairs = ', '.join([f'{i:02X}x' for i in range(250)])  # Over 200 limit
    dod_hex_pairs = ', '.join([f'{i:02X}x' for i in range(300)])  # Over 200 limit

    fdo_script = f"""uni_start_stream <00x>
  man_start_object <view, "">
    man_append_data <{man_hex_pairs}>
    idb_append_data <{idb_hex_pairs}>
    dod_data <{dod_hex_pairs}>
  man_end_object
uni_end_stream <00x>"""

    print(f"\nOriginal script lines: {len(fdo_script.split(chr(10)))}")

    preprocessed = FdoAtomParser.preprocess_script(fdo_script)
    preprocessed_lines = preprocessed.split('\n')

    print(f"Preprocessed script lines: {len(preprocessed_lines)}")

    # Count each type
    man_lines = [l for l in preprocessed_lines if 'man_append_data' in l]
    idb_lines = [l for l in preprocessed_lines if 'idb_append_data' in l]
    dod_lines = [l for l in preprocessed_lines if 'dod_data' in l]

    print(f"\nman_append_data lines: {len(man_lines)} (expected 2: 150+50)")
    print(f"idb_append_data lines: {len(idb_lines)} (expected 2: 200+50)")
    print(f"dod_data lines: {len(dod_lines)} (expected 2: 200+100)")

    if len(man_lines) != 2 or len(idb_lines) != 2 or len(dod_lines) != 2:
        print("\nERROR: Unexpected number of split lines!")
        return False

    print("\nSUCCESS: Full preprocessing works!")
    return True

def test_backward_compatibility():
    """Test that continuous hex format still works (legacy)."""
    print("\n" + "=" * 80)
    print("TEST: Backward compatibility with continuous hex (LEGACY)")
    print("=" * 80)

    # Test continuous hex format (no commas, no 'x' suffix)
    continuous_hex = ''.join([f'{i:02X}' for i in range(250)])  # 500 chars = 250 bytes
    idb_line = f"      idb_append_data <{continuous_hex}>"

    print(f"\nContinuous hex format: {len(continuous_hex)} chars")

    # Should be detected by legacy method
    is_long_legacy = FdoAtomParser._is_long_idb_append_data(idb_line)
    is_long_hex_pairs = FdoAtomParser._is_long_idb_append_data_hex(idb_line)

    print(f"_is_long_idb_append_data() (legacy): {is_long_legacy}")
    print(f"_is_long_idb_append_data_hex() (new): {is_long_hex_pairs}")

    if not is_long_legacy:
        print("ERROR: Legacy method should detect long continuous hex!")
        return False

    if is_long_hex_pairs:
        print("ERROR: New method should NOT detect continuous hex (no commas/x)!")
        return False

    print("\nSUCCESS: Backward compatibility maintained!")
    return True

if __name__ == "__main__":
    success = True
    success &= test_idb_append_data_hex_pairs()
    success &= test_dod_data_hex_pairs()
    success &= test_full_preprocessing()
    success &= test_backward_compatibility()

    if success:
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED!")
        print("=" * 80)
        print("\nFormat Support Summary:")
        print("  man_append_data <\"text\"> - Supported")
        print("  man_append_data <2Ax, 3Bx, ...> - Supported (NEW)")
        print("  idb_append_data <AABBCC> - Supported (LEGACY)")
        print("  idb_append_data <2Ax, 3Bx, ...> - Supported (NEW - PREFERRED)")
        print("  dod_data <AABBCC> - Supported (LEGACY)")
        print("  dod_data <2Ax, 3Bx, ...> - Supported (NEW - PREFERRED)")

    sys.exit(0 if success else 1)
