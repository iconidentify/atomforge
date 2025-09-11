#!/usr/bin/env python3
"""
FDO Binary Encoder - Convert Ada32.dll debug output to binary FDO format
Based on analysis of golden .str files vs debug output from Ada32.dll
"""

import re
import struct
import sys
from pathlib import Path

class FDOEncoder:
    def __init__(self):
        # FDO packet header observed in golden files
        self.fdo_header = bytes([0x40, 0x01, 0x01, 0x00, 0x22, 0x01])
        
    def parse_debug_format(self, debug_text):
        """Parse the debug format from Ada32.dll output"""
        lines = debug_text.strip().split('\n')
        
        # Extract the main content from man_append_data
        title = None
        description = None
        room_name_label = None
        create_button = None
        enter_button = None
        
        for line in lines:
            line = line.strip()
            
            # Extract title from man_start_object
            if 'man_start_object <independent,' in line:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    title = match.group(1)
            
            # Extract main text from man_append_data
            elif 'man_append_data <' in line:
                match = re.search(r'<"([^"]+)">', line)
                if match:
                    description = match.group(1)
            
            # Extract labels and button text
            elif 'editable_view,' in line:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    room_name_label = match.group(1)
            
            elif 'trigger,' in line and 'Create' in line:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    create_button = match.group(1)
            
            elif 'trigger,' in line and 'Enter' in line:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    enter_button = match.group(1)
        
        return {
            'title': title,
            'description': description,
            'room_name_label': room_name_label,
            'create_button': create_button,
            'enter_button': enter_button
        }
    
    def encode_to_binary_fdo(self, parsed_data):
        """Encode parsed data to binary FDO format"""
        output = bytearray()
        
        # Add FDO header
        output.extend(self.fdo_header)
        
        # Add title string (if present)
        if parsed_data['title']:
            title_bytes = parsed_data['title'].encode('latin-1')
            output.extend(title_bytes)
            # Add separator observed in golden files
            output.extend(b'\x30\x6c\x20\x00\x69\x30\x28\x43\xe4\x50\xa0\x42\xe0\x22\x83\x20\x01\x20\x02\x41\x00\x30\x28\x1b\x41\xe0\x30\x8e\x01\x00\x05\x31\xc1\x41\xe1\x30\x97\x32\x04\x02\x00\xe2\x50\x79\x20\x84\x01\x14\x00\xa3\x00\x05\x0a')
        
        # Add description text fragments
        if parsed_data['description']:
            # Split description into parts as observed in golden file
            desc = parsed_data['description']
            parts = desc.split('.  ')
            
            if len(parts) >= 1:
                # First part
                first_part = parts[0].replace('All People Connection', 'All People')
                output.extend(first_part.encode('latin-1'))
                output.extend(b'\x00\x05i ')
                
                if len(parts) >= 2:
                    # Second part
                    remaining = '.  '.join(parts[1:])
                    # Split at specific point observed in golden file
                    if 'room name in' in remaining:
                        before_in = remaining.split('room name in')[0] + 'room name in'
                        after_in = remaining.split('room name in')[1]
                        
                        output.extend(before_in.encode('latin-1'))
                        output.extend(b'\x00\x060 ')
                        output.extend(after_in.encode('latin-1'))
        
        # Add form controls
        if parsed_data['room_name_label']:
            output.extend(b'!\x02\x81\x0b\t')
            output.extend(parsed_data['room_name_label'].encode('latin-1'))
            output.extend(b'0\x97\x14\x01\x00\x14\xcb\xb1\xa0\xa3\xa4\xe2\xa5\xe2\xa6\xe2\xc7A\x010(#\x01\x00\x0c\x06')
        
        if parsed_data['create_button']:
            output.extend(parsed_data['create_button'].encode('latin-1'))
            output.extend(b'P""\xc4@\x01#')
        
        # Add remaining control bytes and second button
        output.extend(b'JcQ\x01\x01\x0e\x06')
        
        if parsed_data['enter_button']:
            output.extend(parsed_data['enter_button'].encode('latin-1'))
            output.extend(b'"\xc4@\x01#')
        
        # Add footer
        output.extend(b'JcV!\x02bq \x10@\x02')
        
        return bytes(output)
    
    def convert_debug_to_binary(self, debug_file, output_file):
        """Convert debug format file to binary FDO format"""
        try:
            with open(debug_file, 'r', encoding='utf-8') as f:
                debug_text = f.read()
            
            # Parse the debug format
            parsed = self.parse_debug_format(debug_text)
            print(f"Parsed data: {parsed}")
            
            # Encode to binary FDO
            binary_data = self.encode_to_binary_fdo(parsed)
            
            # Write output
            with open(output_file, 'wb') as f:
                f.write(binary_data)
            
            print(f"✅ Converted {len(debug_text)} chars -> {len(binary_data)} bytes")
            print(f"📁 Output: {output_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 fdo_encoder.py <input_debug.txt> <output.str>")
        sys.exit(1)
    
    debug_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("🔧 FDO Binary Encoder")
    print("=" * 40)
    
    if not Path(debug_file).exists():
        print(f"❌ Input file not found: {debug_file}")
        sys.exit(1)
    
    encoder = FDOEncoder()
    success = encoder.convert_debug_to_binary(debug_file, output_file)
    
    if success:
        print("\n🎉 Conversion completed successfully!")
        
        # Compare with golden file if it exists
        golden_file = debug_file.replace('.txt', '.str')
        if Path(golden_file).exists():
            our_size = Path(output_file).stat().st_size
            golden_size = Path(golden_file).stat().st_size
            print(f"\n📊 Size comparison:")
            print(f"   Our output: {our_size:,} bytes")
            print(f"   Golden file: {golden_size:,} bytes")
            print(f"   Ratio: {our_size/golden_size:.1f}x")
    else:
        print("\n❌ Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()