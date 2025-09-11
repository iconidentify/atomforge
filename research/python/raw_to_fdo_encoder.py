#!/usr/bin/env python3
"""
Raw Ada32 to FDO Format Encoder
Converts 413-byte raw Ada32 output to 356-byte FDO production format
Based on discovered encoding patterns
"""

def encode_raw_to_fdo(raw_data):
    """Convert raw Ada32 output to FDO format"""
    
    print(f"Input: {len(raw_data)} bytes")
    print(f"Raw header: {raw_data[:8].hex(' ')}")
    
    result = bytearray()
    
    # Step 1: Transform header
    # Raw: 00 01 01 00 01 00 22 01
    # FDO: 40 01 01 00 22 01
    
    if len(raw_data) >= 8 and raw_data[:6] == b'\x00\x01\x01\x00\x01\x00':
        # Remove the extra "01 00" bytes and change 00 to 40
        result.extend(b'\x40\x01\x01\x00')
        result.extend(raw_data[6:])  # Continue with rest of data
    else:
        print("❌ Unexpected header format")
        return None
    
    print(f"After header transform: {len(result)} bytes")
    
    # Step 2: Transform control bytes (10 xx -> 30 xx)
    i = 0
    while i < len(result):
        if result[i] == 0x10:
            result[i] = 0x30
            print(f"Transformed 10 {result[i+1]:02x} -> 30 {result[i+1]:02x} at position {i}")
        i += 1
    
    print(f"After control byte transform: {len(result)} bytes")
    print(f"FDO header: {result[:8].hex(' ')}")
    
    return bytes(result)

def advanced_encode_raw_to_fdo(raw_data):
    """
    More sophisticated encoder that handles the complex transformations
    observed in the byte-by-byte comparison
    """
    
    print(f"=== Advanced Raw-to-FDO Encoding ===")
    print(f"Input: {len(raw_data)} bytes")
    
    if len(raw_data) < 8:
        print("❌ Input too short")
        return None
    
    result = bytearray()
    
    # Header transformation: 00 01 01 00 01 00 22 01 -> 40 01 01 00 22 01
    if raw_data[:6] == b'\x00\x01\x01\x00\x01\x00':
        result.extend(b'\x40\x01\x01\x00')  # New header
        # Skip the extra "01 00" and start from position 6
        pos = 6
    else:
        print("❌ Unexpected header")
        return None
    
    # Process the rest byte by byte with transformation rules
    while pos < len(raw_data):
        byte = raw_data[pos]
        
        # Main transformation rule: 10 xx -> 30 xx
        if byte == 0x10:
            result.append(0x30)
            # The next byte might need additional transformation
            if pos + 1 < len(raw_data):
                next_byte = raw_data[pos + 1]
                
                # Apply specific transformations based on observed patterns
                if next_byte == 0x0c:
                    result.append(0x6c)  # 0c -> 6c (add 0x60)
                else:
                    result.append(next_byte)  # Keep as-is for now
                
                pos += 2  # Skip both bytes
            else:
                pos += 1
        else:
            # For non-control bytes, copy directly
            result.append(byte)
            pos += 1
    
    print(f"Encoded to {len(result)} bytes")
    return bytes(result)

def test_encoder():
    """Test the encoder with our Ada32 output"""
    
    try:
        with open('test_output/clean_AdaAssembleAtomStream.str', 'rb') as f:
            raw_data = f.read()
        print(f"✅ Loaded raw Ada32 output: {len(raw_data)} bytes")
    except FileNotFoundError:
        print("❌ Raw Ada32 output file not found")
        return
    
    # Try basic encoder
    print("\n=== Basic Encoder ===")
    encoded = encode_raw_to_fdo(raw_data)
    
    if encoded:
        # Save result
        with open('test_output/encoded_fdo_basic.str', 'wb') as f:
            f.write(encoded)
        print(f"💾 Saved basic encoding: {len(encoded)} bytes")
        
        # Check if it starts with FDO header
        if len(encoded) >= 2 and encoded[0] == 0x40 and encoded[1] == 0x01:
            print("✅ FDO header detected!")
        
        # Compare size with target
        target_size = 356
        print(f"Target size: {target_size} bytes")
        print(f"Our size: {len(encoded)} bytes")
        print(f"Difference: {len(encoded) - target_size} bytes")
    
    # Try advanced encoder
    print("\n=== Advanced Encoder ===")
    encoded_adv = advanced_encode_raw_to_fdo(raw_data)
    
    if encoded_adv:
        with open('test_output/encoded_fdo_advanced.str', 'wb') as f:
            f.write(encoded_adv)
        print(f"💾 Saved advanced encoding: {len(encoded_adv)} bytes")
        
        # Compare with golden file
        try:
            with open('golden_tests/32-105.str', 'rb') as f:
                golden = f.read()
            
            print(f"\n📊 Comparison with golden file:")
            print(f"Golden: {len(golden)} bytes")
            print(f"Ours:   {len(encoded_adv)} bytes")
            
            if len(encoded_adv) == len(golden):
                print("🎯 SIZE MATCH!")
                
                # Check if content matches
                matches = sum(1 for i in range(len(golden)) if encoded_adv[i] == golden[i])
                print(f"Byte matches: {matches}/{len(golden)} ({matches/len(golden)*100:.1f}%)")
                
                if matches == len(golden):
                    print("🎉 PERFECT MATCH - ENCODER COMPLETE!")
            
        except FileNotFoundError:
            print("❌ Golden file not found for comparison")

if __name__ == "__main__":
    test_encoder()