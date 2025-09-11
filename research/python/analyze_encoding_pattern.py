#!/usr/bin/env python3
"""
Analyze the encoding pattern between raw Ada32 output and FDO format
by comparing our 413-byte output with the 356-byte golden file
"""

def analyze_files():
    print("=== Analyzing Raw vs FDO Encoding Pattern ===\n")
    
    # Load our raw Ada32 output
    try:
        with open('test_output/clean_AdaAssembleAtomStream.str', 'rb') as f:
            raw_data = f.read()
        print(f"✅ Raw Ada32 output: {len(raw_data)} bytes")
    except FileNotFoundError:
        print("❌ Raw Ada32 output file not found")
        return
    
    # Load golden FDO file  
    try:
        with open('golden_tests/32-105.str', 'rb') as f:
            fdo_data = f.read()
        print(f"✅ Golden FDO file: {len(fdo_data)} bytes")
    except FileNotFoundError:
        print("❌ Golden FDO file not found")
        return
    
    print()
    
    # Compare headers
    print("=== Header Analysis ===")
    raw_header = raw_data[:8]
    fdo_header = fdo_data[:8]
    
    print(f"Raw header: {raw_header.hex(' ')}")
    print(f"FDO header: {fdo_header.hex(' ')}")
    print()
    
    # Look for the text "Public Rooms in People Connection" in both
    text = b"Public Rooms in People Connection"
    raw_text_pos = raw_data.find(text)
    fdo_text_pos = fdo_data.find(text)
    
    print(f"Text position in raw: {raw_text_pos}")
    print(f"Text position in FDO: {fdo_text_pos}")
    print()
    
    # Analyze control bytes before and after the text
    if raw_text_pos > 0 and fdo_text_pos > 0:
        print("=== Control Bytes Before Text ===")
        raw_before = raw_data[raw_text_pos-8:raw_text_pos]
        fdo_before = fdo_data[fdo_text_pos-8:fdo_text_pos]
        print(f"Raw: {raw_before.hex(' ')}")
        print(f"FDO: {fdo_before.hex(' ')}")
        print()
        
        print("=== Control Bytes After Text ===")
        text_end_raw = raw_text_pos + len(text)
        text_end_fdo = fdo_text_pos + len(text)
        
        raw_after = raw_data[text_end_raw:text_end_raw+16]
        fdo_after = fdo_data[text_end_fdo:text_end_fdo+16]
        print(f"Raw: {raw_after.hex(' ')}")
        print(f"FDO: {fdo_after.hex(' ')}")
        print()
        
        # Look for patterns in the transformation
        print("=== Pattern Analysis ===")
        print("Looking for transformation rules...")
        
        # Check if there's a simple mapping
        for i in range(min(len(raw_after), len(fdo_after))):
            if raw_after[i] != fdo_after[i]:
                print(f"Byte {i}: {raw_after[i]:02x} -> {fdo_after[i]:02x}")
        
        # Look for the specific pattern we saw: 10 0c -> 30 6c  
        print("\nLooking for 10 xx -> 30 xx pattern...")
        for i in range(len(raw_data) - 1):
            if raw_data[i] == 0x10:
                next_byte = raw_data[i + 1]
                # Look for corresponding pattern in FDO at similar position
                search_start = max(0, i - 50)
                search_end = min(len(fdo_data) - 1, i + 50)
                
                for j in range(search_start, search_end):
                    if j < len(fdo_data) - 1 and fdo_data[j] == 0x30 and fdo_data[j + 1] == next_byte:
                        print(f"Pattern found: 10 {next_byte:02x} -> 30 {next_byte:02x} (raw pos {i}, fdo pos {j})")
                        break

def compare_with_other_samples():
    """Compare with other golden test files to find more patterns"""
    print("\n=== Comparing Multiple Sample Files ===")
    
    import os
    golden_dir = 'golden_tests'
    
    # Find all .str files
    str_files = [f for f in os.listdir(golden_dir) if f.endswith('.str')]
    print(f"Found {len(str_files)} golden .str files")
    
    for str_file in str_files[:5]:  # Check first 5
        try:
            with open(f'{golden_dir}/{str_file}', 'rb') as f:
                data = f.read()
            
            # Check if it's FDO format
            if len(data) >= 2 and data[0] == 0x40 and data[1] == 0x01:
                print(f"✅ {str_file}: {len(data)} bytes, FDO format")
                
                # Look for control patterns
                control_patterns = []
                for i in range(len(data) - 1):
                    if data[i] == 0x30:  # Look for 30 xx patterns
                        control_patterns.append(f"30 {data[i+1]:02x}")
                
                if control_patterns:
                    unique_patterns = list(set(control_patterns))
                    print(f"   Control patterns: {unique_patterns[:10]}")  # Show first 10
                        
        except Exception as e:
            print(f"❌ Error reading {str_file}: {e}")

if __name__ == "__main__":
    analyze_files()
    compare_with_other_samples()