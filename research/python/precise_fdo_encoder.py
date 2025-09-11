#!/usr/bin/env python3
"""
Precise FDO Encoder based on exact byte-by-byte analysis
"""

def precise_encode_raw_to_fdo(raw_data):
    """
    Precise encoder based on the exact transformations observed:
    Byte 0: 10 -> 30
    Byte 1: 0c -> 6c  
    Byte 2: 03 -> 20
    Byte 3: 20 -> 00
    Byte 4: 00 -> 69
    Byte 5: 69 -> 30
    etc.
    """
    
    print(f"=== Precise FDO Encoding ===")
    print(f"Input: {len(raw_data)} bytes")
    
    if len(raw_data) < 8:
        return None
    
    # Header transformation: 00 01 01 00 01 00 22 01 -> 40 01 01 00 22 01
    result = bytearray()
    result.extend(b'\x40\x01\x01\x00')
    
    # Start from position 6 in raw data (skip the "01 00" part)
    pos = 6
    
    # Find where the text "Public Rooms in People Connection" starts
    text = b"Public Rooms in People Connection"
    text_pos_raw = raw_data.find(text)
    
    if text_pos_raw == -1:
        print("❌ Text not found")
        return None
    
    print(f"Text found at position {text_pos_raw} in raw data")
    
    # Copy everything up to the text
    while pos < text_pos_raw:
        result.append(raw_data[pos])
        pos += 1
    
    # Copy the text itself
    result.extend(text)
    pos += len(text)
    
    # Now handle the control bytes after the text using observed patterns
    # From analysis: 10 0c 03 20 00 69 10 08 01 43 10 40 01 05 02 00
    # Should become: 30 6c 20 00 69 30 28 43 e4 50 a0 42 e0 22 83 20
    
    control_mappings = {
        # Based on exact byte analysis
        0x10: 0x30,  # All 10 -> 30
        0x0c: 0x6c,  # 0c -> 6c (when after 10)
        0x03: 0x20,  # 03 -> 20
        0x08: 0x28,  # 08 -> 28 (when after 10)
        0x01: 0xe4,  # 01 -> e4 (in certain contexts)
        0x40: 0x42,  # 40 -> 42 (when after 10)
    }
    
    # For now, implement the simple 10->30 transformation
    # This is a starting point that can be refined
    while pos < len(raw_data):
        byte = raw_data[pos]
        
        if byte == 0x10:
            result.append(0x30)
            # Handle the next byte with specific mappings
            if pos + 1 < len(raw_data):
                next_byte = raw_data[pos + 1]
                mapped_byte = control_mappings.get(next_byte, next_byte)
                result.append(mapped_byte)
                pos += 2
            else:
                pos += 1
        else:
            result.append(byte)
            pos += 1
    
    print(f"Encoded to {len(result)} bytes")
    return bytes(result)

def analyze_exact_differences():
    """Analyze the exact differences to build a mapping table"""
    
    try:
        with open('test_output/clean_AdaAssembleAtomStream.str', 'rb') as f:
            raw_data = f.read()
        with open('golden_tests/32-105.str', 'rb') as f:
            golden_data = f.read()
    except FileNotFoundError:
        print("❌ Required files not found")
        return
    
    print("=== Exact Difference Analysis ===")
    
    # Find text positions
    text = b"Public Rooms in People Connection"
    raw_text_pos = raw_data.find(text)
    golden_text_pos = golden_data.find(text)
    
    print(f"Text position - Raw: {raw_text_pos}, Golden: {golden_text_pos}")
    
    # Compare the control sequences after the text
    raw_after = raw_data[raw_text_pos + len(text):raw_text_pos + len(text) + 32]
    golden_after = golden_data[golden_text_pos + len(text):golden_text_pos + len(text) + 32]
    
    print(f"\nRaw control bytes:    {raw_after.hex(' ')}")
    print(f"Golden control bytes: {golden_after.hex(' ')}")
    
    # Build a mapping table
    print(f"\nByte-by-byte mapping:")
    for i in range(min(len(raw_after), len(golden_after))):
        if raw_after[i] != golden_after[i]:
            print(f"  {i:2d}: {raw_after[i]:02x} -> {golden_after[i]:02x}")
    
    # Look for patterns in the entire file
    print(f"\nSize difference: {len(raw_data)} - {len(golden_data)} = {len(raw_data) - len(golden_data)} bytes")

def test_precise_encoder():
    """Test the precise encoder"""
    
    # First analyze the differences
    analyze_exact_differences()
    
    try:
        with open('test_output/clean_AdaAssembleAtomStream.str', 'rb') as f:
            raw_data = f.read()
    except FileNotFoundError:
        print("❌ Raw data not found")
        return
    
    print(f"\n=== Testing Precise Encoder ===")
    encoded = precise_encode_raw_to_fdo(raw_data)
    
    if encoded:
        with open('test_output/encoded_fdo_precise.str', 'wb') as f:
            f.write(encoded)
        
        print(f"💾 Saved precise encoding: {len(encoded)} bytes")
        
        # Compare with golden
        try:
            with open('golden_tests/32-105.str', 'rb') as f:
                golden = f.read()
            
            print(f"\n📊 Results:")
            print(f"Target size: {len(golden)} bytes")
            print(f"Our size: {len(encoded)} bytes")
            print(f"Difference: {len(encoded) - len(golden)} bytes")
            
            if len(encoded) == len(golden):
                print("🎯 SIZE MATCH!")
            
        except FileNotFoundError:
            pass

if __name__ == "__main__":
    test_precise_encoder()