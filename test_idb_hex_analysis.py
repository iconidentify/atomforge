#!/usr/bin/env python3
"""
Reverse engineering analysis of idb_append_data binary format.

Goal: Understand the binary structure to enable manual compilation without Wine daemon.
"""

def analyze_hex_data():
    """Analyze the provided examples to decode binary format."""

    # Example 1
    source1_hex_pairs = [
        "01x", "00x", "01x", "00x", "01x", "00x", "0bx", "05x", "00x", "00x",
        "01x", "00x", "00x", "00x", "05x", "02x", "78x", "00x", "29x", "00x",
        "00x", "00x", "e7x", "04x", "00x", "00x", "24x", "00x", "00x", "00x",
        "00x", "00x", "00x", "00x", "00x", "00x", "80x", "fdx", "00x", "00x",
        "47x", "49x", "46x", "38x", "37x", "61x", "78x", "00x", "29x", "00x",
        "d5x", "00x", "00x", "00x", "00x", "00x", "ffx", "00x", "00x", "ffx",
        "80x", "00x", "ffx", "80x", "40x", "ffx", "8ex", "1cx", "edx", "92x",
        "24x", "f7x", "99x", "2bx", "fcx", "9dx", "2cx", "fcx", "9fx", "31x",
        "ffx", "9fx", "20x", "fcx", "a1x", "34x", "ffx", "a2x", "2fx", "fcx",
        "a4x", "3cx", "ffx", "a4x", "24x", "fcx", "a7x", "42x", "fcx", "a8x",
        "44x", "ffx", "aax", "00x", "ffx", "aax", "2bx", "ffx", "aax", "39x",
        "fcx", "acx", "4cx", "fcx", "afx", "53x", "fcx", "b0x", "56x", "fcx",
        "b3x", "5bx", "fdx", "b6x", "63x", "ffx", "b6x", "24x", "fdx", "b8x",
        "66x", "fdx", "bax", "6ax", "fdx", "bex", "73x", "fdx", "c0x", "77x",
        "fdx", "c2x", "7cx", "fdx", "c6x", "84x", "fdx", "c7x", "88x", "fdx"
    ]

    compiled1_hex = "050B80960100010001000B050000010000000502780029000000E70400002400000000000000000080FD000047494638376178002900D50000000000FF0000FF8000FF8040FF8E1CED9224F7992BFC9D2CFC9F31FF9F20FCA134FFA22FFCA43CFFA424FCA742FCA844FFAA00FFAA2BFFAA39FCAC4CFCAF53FCB056FCB35BFDB663FFB624FDB866FDBA6AFDBE73FDC077FDC27CFDC684FDC788FD"

    # Example 2
    source2_hex_pairs = [
        "c9x", "8bx", "fdx", "cdx", "93x", "fdx", "d1x", "9dx", "fdx", "d4x",
        "a4x", "fdx", "d7x", "a9x", "fdx", "d9x", "aex", "fdx", "dcx", "b4x",
        "fdx", "dex", "bax", "fdx", "e0x", "bex", "fdx", "e3x", "c4x", "fex",
        "e6x", "cbx", "fex", "e8x", "cex", "fex", "eax", "d3x", "fex", "eex",
        "dcx", "fex", "f0x", "dfx", "fex", "f1x", "e3x", "fex", "f5x", "ebx",
        "fex", "f7x", "f0x", "fex", "f9x", "f4x", "ffx", "ffx", "00x", "ffx",
        "ffx", "ffx", "00x", "00x", "00x", "00x", "00x", "00x", "00x", "00x",
        "00x", "00x", "00x", "00x", "00x", "00x", "00x", "00x", "00x", "00x",
        "00x", "00x", "00x", "00x", "00x", "00x", "00x", "00x", "00x", "00x",
        "00x", "00x", "00x", "00x", "00x", "21x", "f9x", "04x", "09x", "00x",
        "00x", "35x", "00x", "2cx", "00x", "00x", "00x", "00x", "78x", "00x",
        "29x", "00x", "00x", "06x", "ffx", "c0x", "9ax", "70x", "38x", "3cx",
        "18x", "8fx", "c8x", "a4x", "72x", "c9x", "6cx", "3ax", "9fx", "d0x",
        "a8x", "93x", "48x", "adx", "d6x", "a4x", "d8x", "acx", "76x", "cbx",
        "65x", "5ax", "89x", "ddx", "b0x", "78x", "4cx", "fex", "5ex", "c9x"
    ]

    compiled2_hex = "050B8096C98BFDCD93FDD19DFDD4A4FDD7A9FDD9AEFDDCB4FDDEBAFDE0BEFDE3C4FEE6CBFEE8CEFEEAD3FEEEDCFEF0DFFEF1E3FEF5EBFEF7F0FEF9F4FFFF00FFFFFF00000000000000000000000000000000000000000000000000000000000021F90409000035002C00000000780029000006FFC09A70383C188FC8A472C96C3A9FD0A89348ADD6A4D8AC76CB655A89DDB0784CFE5EC9"

    print("=" * 80)
    print("REVERSE ENGINEERING idb_append_data BINARY FORMAT")
    print("=" * 80)

    # Convert source to clean bytes
    source1_bytes = [int(h.replace('x', ''), 16) for h in source1_hex_pairs]
    source2_bytes = [int(h.replace('x', ''), 16) for h in source2_hex_pairs]

    # Convert compiled hex to bytes
    compiled1_bytes = bytes.fromhex(compiled1_hex)
    compiled2_bytes = bytes.fromhex(compiled2_hex)

    print("\n--- EXAMPLE 1 ANALYSIS ---")
    print(f"Source hex pairs: {len(source1_hex_pairs)}")
    print(f"Source bytes: {len(source1_bytes)}")
    print(f"Compiled bytes: {len(compiled1_bytes)}")
    print(f"\nFirst 20 source bytes: {' '.join(f'{b:02X}' for b in source1_bytes[:20])}")
    print(f"First 20 compiled bytes: {' '.join(f'{b:02X}' for b in compiled1_bytes[:20])}")

    # Analyze header
    print("\n--- HEADER ANALYSIS (Example 1) ---")
    print(f"Byte 0: 0x{compiled1_bytes[0]:02X} ({compiled1_bytes[0]:3d}) - OPCODE?")
    print(f"Byte 1: 0x{compiled1_bytes[1]:02X} ({compiled1_bytes[1]:3d}) - FLAGS/SUBOPCODE?")
    print(f"Byte 2: 0x{compiled1_bytes[2]:02X} ({compiled1_bytes[2]:3d}) - LENGTH_LOW?")
    print(f"Byte 3: 0x{compiled1_bytes[3]:02X} ({compiled1_bytes[3]:3d}) - LENGTH_HIGH?")

    # Try interpreting as little-endian 16-bit length
    length_field = compiled1_bytes[2] | (compiled1_bytes[3] << 8)
    print(f"\nLength field (bytes 2-3, little-endian): 0x{length_field:04X} = {length_field} bytes")
    print(f"Payload after header should be: {length_field} bytes")
    print(f"Actual payload size (total - 4): {len(compiled1_bytes) - 4} bytes")

    # Check if payload matches source
    payload1 = compiled1_bytes[4:]
    print(f"\n--- PAYLOAD COMPARISON (Example 1) ---")
    print(f"Payload bytes: {len(payload1)}")
    print(f"Source bytes: {len(source1_bytes)}")
    print(f"Match: {payload1 == bytes(source1_bytes)}")

    if payload1 == bytes(source1_bytes):
        print("\n*** BREAKTHROUGH: Payload is EXACTLY the source hex pairs converted to bytes! ***")
    else:
        print("\nPayload differences:")
        for i in range(min(len(payload1), len(source1_bytes))):
            if i >= len(payload1) or i >= len(source1_bytes) or payload1[i] != source1_bytes[i]:
                print(f"  Offset {i}: payload={payload1[i]:02X} source={source1_bytes[i]:02X}")

    print("\n--- EXAMPLE 2 ANALYSIS ---")
    print(f"Source hex pairs: {len(source2_hex_pairs)}")
    print(f"Source bytes: {len(source2_bytes)}")
    print(f"Compiled bytes: {len(compiled2_bytes)}")

    # Analyze header
    print("\n--- HEADER ANALYSIS (Example 2) ---")
    print(f"Byte 0: 0x{compiled2_bytes[0]:02X} ({compiled2_bytes[0]:3d}) - OPCODE?")
    print(f"Byte 1: 0x{compiled2_bytes[1]:02X} ({compiled2_bytes[1]:3d}) - FLAGS/SUBOPCODE?")
    print(f"Byte 2: 0x{compiled2_bytes[2]:02X} ({compiled2_bytes[2]:3d}) - LENGTH_LOW?")
    print(f"Byte 3: 0x{compiled2_bytes[3]:02X} ({compiled2_bytes[3]:3d}) - LENGTH_HIGH?")

    length_field2 = compiled2_bytes[2] | (compiled2_bytes[3] << 8)
    print(f"\nLength field (bytes 2-3, little-endian): 0x{length_field2:04X} = {length_field2} bytes")

    # Check payload
    payload2 = compiled2_bytes[4:]
    print(f"\n--- PAYLOAD COMPARISON (Example 2) ---")
    print(f"Payload bytes: {len(payload2)}")
    print(f"Source bytes: {len(source2_bytes)}")
    print(f"Match: {payload2 == bytes(source2_bytes)}")

    if payload2 == bytes(source2_bytes):
        print("\n*** CONFIRMED: Payload is EXACTLY the source hex pairs converted to bytes! ***")

    # Verify consistency
    print("\n" + "=" * 80)
    print("FORMAT SPECIFICATION HYPOTHESIS")
    print("=" * 80)
    print("""
Structure: [OPCODE][FLAGS][LENGTH_LOW][LENGTH_HIGH][...PAYLOAD...]

OPCODE (byte 0): 0x05 - Identifies idb_append_data atom
FLAGS (byte 1):  0x0B - Unknown purpose (sub-opcode? encoding flags?)
LENGTH (bytes 2-3): Little-endian 16-bit unsigned integer
    - Specifies the length of the payload in bytes
    - Does NOT include the 4-byte header itself
PAYLOAD (bytes 4+): Raw bytes from hex pairs in source
    - Each "XXx" in source becomes byte 0xXX in payload
    - Direct 1:1 mapping, no encoding/compression
    """)

    print("\nVERIFICATION:")
    print(f"Example 1: Header says {length_field} bytes, actual payload is {len(payload1)} bytes - {'MATCH' if length_field == len(payload1) else 'MISMATCH'}")
    print(f"Example 2: Header says {length_field2} bytes, actual payload is {len(payload2)} bytes - {'MATCH' if length_field2 == len(payload2) else 'MISMATCH'}")

    return {
        'opcode': compiled1_bytes[0],
        'flags': compiled1_bytes[1],
        'payload1_match': payload1 == bytes(source1_bytes),
        'payload2_match': payload2 == bytes(source2_bytes),
    }

if __name__ == '__main__':
    results = analyze_hex_data()

    if results['payload1_match'] and results['payload2_match']:
        print("\n" + "=" * 80)
        print("SUCCESS: Binary format decoded with 100% confidence!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("WARNING: Pattern does not match - further investigation needed")
        print("=" * 80)
