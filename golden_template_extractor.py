#!/usr/bin/env python3
"""
Golden Template Extractor - Extract exact byte patterns from golden FDO files
"""

def extract_fdo_template(golden_file):
    """Extract the exact template from a golden FDO file"""
    
    with open(golden_file, 'rb') as f:
        data = f.read()
    
    print(f"=== Golden Template Analysis: {golden_file} ===")
    print(f"Total size: {len(data)} bytes")
    
    # Key strings to find
    strings = {
        'title': b'Public Rooms in People Connection',
        'all_people': b'All People',
        'connection_rooms': b' Connection rooms are empty.  To create a new public room or enter a private room, enter the room name in',
        'the_box': b' the box below and click the appropriate button.',
        'room_name': b'Room name:',
        'create_room': b'Create Room',
        'enter_private': b'Enter Private'
    }
    
    # Find positions of each string
    positions = {}
    for name, string in strings.items():
        pos = data.find(string)
        if pos != -1:
            positions[name] = (pos, pos + len(string))
            print(f"{name:15}: pos {pos:3d}-{pos + len(string):3d} = {string}")
    
    print("\n=== Byte Templates ===")
    
    # Extract templates between strings
    templates = {}
    
    if 'title' in positions:
        # Header (before title)
        header = data[:positions['title'][0]]
        templates['header'] = header
        print(f"Header ({len(header)} bytes): {' '.join(f'{b:02x}' for b in header)}")
    
    if 'title' in positions and 'all_people' in positions:
        # Between title and "All People"
        start = positions['title'][1]
        end = positions['all_people'][0]
        sep1 = data[start:end]
        templates['title_to_all_people'] = sep1
        print(f"Title->AllPeople ({len(sep1)} bytes): {' '.join(f'{b:02x}' for b in sep1)}")
    
    if 'all_people' in positions and 'connection_rooms' in positions:
        # Between "All People" and " Connection rooms..."
        start = positions['all_people'][1]
        end = positions['connection_rooms'][0]
        sep2 = data[start:end]
        templates['all_people_to_connection'] = sep2
        print(f"AllPeople->Connection ({len(sep2)} bytes): {' '.join(f'{b:02x}' for b in sep2)}")
    
    if 'connection_rooms' in positions and 'the_box' in positions:
        # Between "...room name in" and " the box..."
        start = positions['connection_rooms'][1]
        end = positions['the_box'][0]
        sep3 = data[start:end]
        templates['connection_to_box'] = sep3
        print(f"Connection->Box ({len(sep3)} bytes): {' '.join(f'{b:02x}' for b in sep3)}")
        
    if 'the_box' in positions and 'room_name' in positions:
        # Between "...button." and "Room name:"
        start = positions['the_box'][1]
        end = positions['room_name'][0]
        sep4 = data[start:end]
        templates['box_to_room_name'] = sep4
        print(f"Box->RoomName ({len(sep4)} bytes): {' '.join(f'{b:02x}' for b in sep4)}")
    
    if 'room_name' in positions and 'create_room' in positions:
        # Between "Room name:" and "Create Room"
        start = positions['room_name'][1]
        end = positions['create_room'][0]
        sep5 = data[start:end]
        templates['room_name_to_create'] = sep5
        print(f"RoomName->Create ({len(sep5)} bytes): {' '.join(f'{b:02x}' for b in sep5)}")
    
    if 'create_room' in positions and 'enter_private' in positions:
        # Between "Create Room" and "Enter Private"
        start = positions['create_room'][1]
        end = positions['enter_private'][0]
        sep6 = data[start:end]
        templates['create_to_enter'] = sep6
        print(f"Create->Enter ({len(sep6)} bytes): {' '.join(f'{b:02x}' for b in sep6)}")
    
    if 'enter_private' in positions:
        # Footer (after "Enter Private")
        start = positions['enter_private'][1]
        footer = data[start:]
        templates['footer'] = footer
        print(f"Footer ({len(footer)} bytes): {' '.join(f'{b:02x}' for b in footer)}")
    
    return templates

def generate_template_encoder(templates):
    """Generate Python code for exact template-based encoder"""
    
    print("\n=== Generated Template Code ===")
    print("def encode_with_templates(parsed_data):")
    print("    output = bytearray()")
    print()
    
    if 'header' in templates:
        header_hex = ''.join(f'\\x{b:02x}' for b in templates['header'])
        print(f"    # Header")
        print(f"    output.extend(b'{header_hex}')")
        print()
    
    print("    # Title")
    print("    if parsed_data['title']:")
    print("        output.extend(parsed_data['title'].encode('latin-1'))")
    
    if 'title_to_all_people' in templates:
        sep_hex = ''.join(f'\\x{b:02x}' for b in templates['title_to_all_people'])
        print(f"        output.extend(b'{sep_hex}')")
    print()
    
    # Continue with other sections...
    sections = [
        ('all_people_to_connection', "All People", 'all_people_connection'),
        ('connection_to_box', "Connection text", 'connection_text'),
        ('box_to_room_name', "Box text", 'box_text'),
        ('room_name_to_create', "Room name label", 'room_name_label'),
        ('create_to_enter', "Create button", 'create_button'),
        ('footer', "Enter button + footer", 'enter_button')
    ]
    
    for template_key, comment, data_key in sections:
        if template_key in templates:
            sep_hex = ''.join(f'\\x{b:02x}' for b in templates[template_key])
            print(f"    # {comment}")
            if template_key != 'footer':
                print(f"    # Add content here")
                print(f"    output.extend(b'{sep_hex}')")
            else:
                print(f"    output.extend(parsed_data['{data_key}'].encode('latin-1'))")
                print(f"    output.extend(b'{sep_hex}')")
            print()
    
    print("    return bytes(output)")

if __name__ == "__main__":
    templates = extract_fdo_template('golden_tests/32-105.str')
    generate_template_encoder(templates)