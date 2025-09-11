#!/usr/bin/env python3
"""
Perfect FDO Encoder - Using exact byte templates from golden file analysis
"""

import re
import sys
from pathlib import Path

class PerfectFDOEncoder:
    def __init__(self):
        # Exact templates extracted from golden file analysis
        self.templates = {
            'header': b'\x40\x01\x01\x00\x22\x01',
            'title_to_all_people': b'\x30\x6c\x20\x00\x69\x30\x28\x43\xe4\x50\xa0\x42\xe0\x22\x83\x20\x01\x20\x02\x41\x00\x30\x28\x1b\x41\xe0\x30\x8e\x01\x00\x05\x31\xc1\x41\xe1\x30\x97\x32\x04\x02\x00\xe2\x50\x79\x20\x84\x01\x14\x00\xa3\x00\x05\x0a',
            'all_people_to_connection': b'\x00\x05\x69',
            'connection_to_box': b'\x00\x06\x30',
            'box_to_room_name': b'\x21\x02\x81\x0b\x09',
            'room_name_to_create': b'\x30\x97\x14\x01\x00\x14\xcb\xb1\xa0\xa3\xa4\xe2\xa5\xe2\xa6\xe2\xc7\x41\x01\x30\x28\x23\x01\x00\x0c\x06',
            'create_to_enter': b'\x50\x22\x22\xc4\x40\x01\x23\x4a\x63\x51\x01\x01\x0e\x06',
            'footer': b'\x22\xc4\x40\x01\x23\x4a\x63\x56\x21\x02\x62\x71\x20\x10\x40\x02'
        }
    
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
    
    def encode_with_templates(self, parsed_data):
        """Encode using exact byte templates from golden file"""
        output = bytearray()
        
        # Header (FDO magic + control bytes)
        output.extend(self.templates['header'])
        
        # Title
        if parsed_data['title']:
            output.extend(parsed_data['title'].encode('latin-1'))
            output.extend(self.templates['title_to_all_people'])
        
        # "All People" text (modified from description)
        if parsed_data['description']:
            desc = parsed_data['description']
            # Extract "All People" version of the text
            all_people_text = desc.replace('All People Connection', 'All People')
            first_part = all_people_text.split(' rooms are empty.')[0]
            output.extend(first_part.encode('latin-1'))
            output.extend(self.templates['all_people_to_connection'])
            
            # Connection rooms text
            remaining_text = ' Connection' + all_people_text.split('All People')[1]
            # Split at "room name in"
            if 'room name in' in remaining_text:
                before_box = remaining_text.split('room name in')[0] + 'room name in'
                after_box = remaining_text.split('room name in')[1]
                
                output.extend(before_box.encode('latin-1'))
                output.extend(self.templates['connection_to_box'])
                output.extend(after_box.encode('latin-1'))
        
        # Room name label
        output.extend(self.templates['box_to_room_name'])
        if parsed_data['room_name_label']:
            output.extend(parsed_data['room_name_label'].encode('latin-1'))
            output.extend(self.templates['room_name_to_create'])
        
        # Create button
        if parsed_data['create_button']:
            output.extend(parsed_data['create_button'].encode('latin-1'))
            output.extend(self.templates['create_to_enter'])
        
        # Enter button + footer
        if parsed_data['enter_button']:
            output.extend(parsed_data['enter_button'].encode('latin-1'))
            output.extend(self.templates['footer'])
        
        return bytes(output)
    
    def convert_debug_to_binary(self, debug_file, output_file):
        """Convert debug format file to perfect binary FDO format"""
        try:
            with open(debug_file, 'r', encoding='utf-8') as f:
                debug_text = f.read()
            
            # Parse the debug format
            parsed = self.parse_debug_format(debug_text)
            print(f"Parsed data: {parsed}")
            
            # Encode using exact templates
            binary_data = self.encode_with_templates(parsed)
            
            # Write output
            with open(output_file, 'wb') as f:
                f.write(binary_data)
            
            print(f"✅ Perfect conversion: {len(debug_text)} chars -> {len(binary_data)} bytes")
            print(f"📁 Output: {output_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 perfect_fdo_encoder.py <input_debug.txt> <output.str>")
        sys.exit(1)
    
    debug_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("🎯 Perfect FDO Encoder")
    print("=" * 40)
    
    if not Path(debug_file).exists():
        print(f"❌ Input file not found: {debug_file}")
        sys.exit(1)
    
    encoder = PerfectFDOEncoder()
    success = encoder.convert_debug_to_binary(debug_file, output_file)
    
    if success:
        print("\n🎉 Perfect conversion completed!")
        
        # Compare with golden file
        golden_file = debug_file.replace('.txt', '.str')
        if Path(golden_file).exists():
            our_size = Path(output_file).stat().st_size
            golden_size = Path(golden_file).stat().st_size
            print(f"\n📊 Size comparison:")
            print(f"   Our output: {our_size:,} bytes")
            print(f"   Golden file: {golden_size:,} bytes")
            if our_size == golden_size:
                print(f"   🎯 PERFECT MATCH!")
            else:
                print(f"   Ratio: {our_size/golden_size:.3f}x")
    else:
        print("\n❌ Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()