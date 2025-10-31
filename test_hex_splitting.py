#!/usr/bin/env python3
"""
Test script for hex-pair man_append_data splitting
"""

import sys
sys.path.insert(0, '/Users/chrisk/Documents/aol_lfg/source/atomforge/api/src')

from fdo_atom_parser import FdoAtomParser

def test_hex_splitting():
    """Test that long hex-pair man_append_data lines are split correctly."""

    # Create a test case with 200 hex pairs (should be split into 2 chunks of 150 + 50)
    hex_pairs = ', '.join([f'{i:02X}x' for i in range(200)])
    test_line = f"      man_append_data <{hex_pairs}>"

    print("=" * 80)
    print("TEST: Long hex-pair man_append_data splitting")
    print("=" * 80)
    print(f"\nOriginal line length: {len(test_line)} characters")
    print(f"Number of hex pairs: 200")
    print(f"First 100 chars: {test_line[:100]}...")
    print(f"\nExpected: Split into 2 lines (150 pairs + 50 pairs)")
    print(f"Max pairs per line: {FdoAtomParser.MAX_MAN_APPEND_DATA_HEX_PAIRS}")

    # Test detection
    is_long = FdoAtomParser._is_long_append_data_hex(test_line)
    print(f"\n_is_long_append_data_hex() result: {is_long}")

    if not is_long:
        print("ERROR: Failed to detect long hex-pair format!")
        return False

    # Test splitting
    split_lines = FdoAtomParser._split_append_data_hex_line(test_line)
    print(f"\nActual: Split into {len(split_lines)} lines")

    for i, line in enumerate(split_lines):
        pairs = [p.strip() for p in FdoAtomParser._extract_hex_from_man_append_data(line).split(',') if p.strip()]
        print(f"  Line {i+1}: {len(pairs)} pairs, first 80 chars: {line[:80]}...")

    # Verify results
    if len(split_lines) != 2:
        print(f"\nERROR: Expected 2 lines, got {len(split_lines)}")
        return False

    # Check first line has 150 pairs
    first_pairs = [p.strip() for p in FdoAtomParser._extract_hex_from_man_append_data(split_lines[0]).split(',') if p.strip()]
    if len(first_pairs) != 150:
        print(f"\nERROR: First line should have 150 pairs, got {len(first_pairs)}")
        return False

    # Check second line has 50 pairs
    second_pairs = [p.strip() for p in FdoAtomParser._extract_hex_from_man_append_data(split_lines[1]).split(',') if p.strip()]
    if len(second_pairs) != 50:
        print(f"\nERROR: Second line should have 50 pairs, got {len(second_pairs)}")
        return False

    print("\nSUCCESS: Splitting works correctly!")

    # Test full preprocessing
    print("\n" + "=" * 80)
    print("TEST: Full preprocess_script() integration")
    print("=" * 80)

    fdo_script = f"""uni_start_stream <00x>
  man_start_object <view, "">
{test_line}
  man_end_object
uni_end_stream <00x>"""

    print(f"\nOriginal script lines: {len(fdo_script.split(chr(10)))}")

    preprocessed = FdoAtomParser.preprocess_script(fdo_script)
    preprocessed_lines = preprocessed.split('\n')

    print(f"Preprocessed script lines: {len(preprocessed_lines)}")

    # Count man_append_data lines
    append_lines = [l for l in preprocessed_lines if 'man_append_data' in l]
    print(f"man_append_data lines: {len(append_lines)}")

    if len(append_lines) != 2:
        print(f"\nERROR: Expected 2 man_append_data lines, got {len(append_lines)}")
        return False

    print("\nSUCCESS: Full preprocessing works correctly!")
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = test_hex_splitting()
    sys.exit(0 if success else 1)
