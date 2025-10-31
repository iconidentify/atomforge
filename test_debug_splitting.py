#!/usr/bin/env python3
"""
Debug script to investigate splitting behavior
"""

import sys
sys.path.insert(0, '/Users/chrisk/Documents/aol_lfg/source/atomforge/api/src')

from fdo_atom_parser import FdoAtomParser

# Create hex pairs
idb_hex_pairs = ', '.join([f'{i:02X}x' for i in range(250)])  # 250 pairs

test_line = f"    idb_append_data <{idb_hex_pairs}>"

print("Testing idb_append_data with 250 hex pairs")
print(f"Line: {test_line[:100]}...")
print()

# Check what each method detects
is_long_legacy = FdoAtomParser._is_long_idb_append_data(test_line)
is_long_hex = FdoAtomParser._is_long_idb_append_data_hex(test_line)

print(f"_is_long_idb_append_data (legacy): {is_long_legacy}")
print(f"_is_long_idb_append_data_hex (new): {is_long_hex}")
print()

# Try extracting with both methods
legacy_content = FdoAtomParser._extract_hex_from_idb_append_data(test_line)
hex_pair_content = FdoAtomParser._extract_hex_pairs_from_idb_append_data(test_line)

print(f"Legacy extraction length: {len(legacy_content) if legacy_content else 0}")
print(f"Hex-pair extraction length: {len(hex_pair_content) if hex_pair_content else 0}")
print()

# Now test through preprocessor
script = f"""uni_start_stream <00x>
{test_line}
uni_end_stream <00x>"""

preprocessed = FdoAtomParser.preprocess_script(script)
lines = [l for l in preprocessed.split('\n') if 'idb_append_data' in l]

print(f"After preprocessing: {len(lines)} idb_append_data lines")
for i, line in enumerate(lines):
    print(f"  Line {i+1}: {line[:80]}...")
