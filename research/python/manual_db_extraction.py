#!/usr/bin/env python3
"""
Manual extraction from main.IDX to verify the encoding
and understand how the database functions should work
"""

def extract_record_manually():
    """Extract the 32-105 record from position 23057"""
    
    try:
        with open('golden_tests/main.IDX', 'rb') as f:
            # Go to the known position of 32-105 record
            f.seek(23057)
            data = f.read(356)  # Read 356 bytes
        
        print(f"✅ Extracted {len(data)} bytes from position 23057")
        print(f"First 16 bytes: {data[:16].hex(' ')}")
        
        # Check if this is FDO format
        if len(data) >= 2 and data[0] == 0x40 and data[1] == 0x01:
            print("✅ FDO format confirmed")
            
            # Save this extraction
            with open('test_output/manual_extracted_32-105.str', 'wb') as f:
                f.write(data)
            print("💾 Saved manual extraction")
            
            # Compare with the golden file
            try:
                with open('golden_tests/32-105.str', 'rb') as f:
                    golden = f.read()
                
                print(f"\n📊 Comparison:")
                print(f"Manual extraction: {len(data)} bytes")
                print(f"Golden file: {len(golden)} bytes")
                
                if data == golden:
                    print("🎉 PERFECT MATCH! Manual extraction equals golden file")
                    return True
                else:
                    print("❌ Files differ")
                    
                    # Show differences
                    for i in range(min(len(data), len(golden))):
                        if data[i] != golden[i]:
                            print(f"Diff at byte {i}: manual={data[i]:02x}, golden={golden[i]:02x}")
                            if i > 10:  # Don't show too many differences
                                break
                            
            except FileNotFoundError:
                print("❌ Golden file not found")
                
        else:
            print("❌ Not FDO format")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return False

def find_all_records():
    """Scan the database file to find all record positions"""
    
    print("\n=== Scanning main.IDX for all records ===")
    
    try:
        with open('golden_tests/main.IDX', 'rb') as f:
            data = f.read()
        
        print(f"Database size: {len(data):,} bytes")
        
        # Look for FDO headers (40 01)
        fdo_positions = []
        for i in range(len(data) - 1):
            if data[i] == 0x40 and data[i + 1] == 0x01:
                fdo_positions.append(i)
        
        print(f"Found {len(fdo_positions)} potential FDO records")
        
        # Analyze each position
        for i, pos in enumerate(fdo_positions[:10]):  # Check first 10
            print(f"\nRecord {i+1} at position {pos}:")
            
            # Try to determine record size by looking for next FDO header
            if i + 1 < len(fdo_positions):
                record_size = fdo_positions[i + 1] - pos
            else:
                # For last record, estimate based on remaining data
                record_size = min(1000, len(data) - pos)  # Max 1000 bytes
            
            record_data = data[pos:pos + record_size]
            print(f"  Size: ~{len(record_data)} bytes")
            print(f"  First 16 bytes: {record_data[:16].hex(' ')}")
            
            # Look for text content
            text_content = ""
            for j in range(16, min(100, len(record_data))):
                if 32 <= record_data[j] <= 126:  # Printable ASCII
                    text_content += chr(record_data[j])
                else:
                    if len(text_content) > 5:  # Found some text
                        break
                    text_content = ""
            
            if text_content:
                print(f"  Text content: {text_content[:50]}...")
                
                # Check if this is our target record
                if "Public Rooms in People Connection" in text_content:
                    print(f"  🎯 FOUND 32-105 RECORD at position {pos}!")
                    
                    # Save this record
                    with open('test_output/scanned_32-105.str', 'wb') as f:
                        f.write(record_data)
                    print(f"  💾 Saved scanned record ({len(record_data)} bytes)")
                    
    except Exception as e:
        print(f"❌ Error scanning database: {e}")

def analyze_db_structure():
    """Try to understand the database structure"""
    
    print("\n=== Analyzing Database Structure ===")
    
    try:
        with open('golden_tests/main.IDX', 'rb') as f:
            # Read the first 1024 bytes to look for header/index structure
            header = f.read(1024)
        
        print(f"Database header (first 64 bytes):")
        print(header[:64].hex(' '))
        
        # Look for patterns that might indicate record table/index
        print(f"\nLooking for record indices...")
        
        # Search for our known values
        known_size = 356
        known_pos = 23057
        
        # Convert to different byte representations
        size_bytes = [
            known_size.to_bytes(4, 'little'),
            known_size.to_bytes(4, 'big'),
            known_size.to_bytes(2, 'little'),
            known_size.to_bytes(2, 'big')
        ]
        
        pos_bytes = [
            known_pos.to_bytes(4, 'little'),
            known_pos.to_bytes(4, 'big')
        ]
        
        print(f"Searching for size {known_size} in various formats:")
        for i, sb in enumerate(size_bytes):
            if sb in header:
                pos = header.find(sb)
                print(f"  Found size format {i} at header position {pos}")
        
        print(f"Searching for position {known_pos} in various formats:")
        for i, pb in enumerate(pos_bytes):
            if pb in header:
                pos = header.find(pb)
                print(f"  Found position format {i} at header position {pos}")
                
    except Exception as e:
        print(f"❌ Error analyzing structure: {e}")

if __name__ == "__main__":
    print("=== Manual Database Analysis ===")
    
    # Step 1: Extract the known record manually
    success = extract_record_manually()
    
    # Step 2: Find all records in the database
    find_all_records()
    
    # Step 3: Analyze database structure
    analyze_db_structure()
    
    if success:
        print(f"\n🎯 SUCCESS: Manual extraction works perfectly!")
        print(f"This proves the encoding is already done in the database.")
        print(f"Now we need to find how to save raw Ada32 output to get this encoding.")
    else:
        print(f"\n❌ Manual extraction failed - need to investigate further")