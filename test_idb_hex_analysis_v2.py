#!/usr/bin/env python3
"""
Reverse engineering analysis of idb_append_data binary format - FIXED VERSION.

The key insight: Little-endian 16-bit length field should be interpreted correctly!
"""

def analyze_hex_data_v2():
    """Analyze with corrected little-endian interpretation."""

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
    print("REVERSE ENGINEERING idb_append_data BINARY FORMAT - V2")
    print("=" * 80)

    # Convert source to clean bytes
    source1_bytes = [int(h.replace('x', ''), 16) for h in source1_hex_pairs]
    source2_bytes = [int(h.replace('x', ''), 16) for h in source2_hex_pairs]

    # Convert compiled hex to bytes
    compiled1_bytes = bytes.fromhex(compiled1_hex)
    compiled2_bytes = bytes.fromhex(compiled2_hex)

    print("\n--- EXAMPLE 1 DETAILED ANALYSIS ---")
    print(f"Source hex pairs: {len(source1_hex_pairs)}")
    print(f"Compiled total bytes: {len(compiled1_bytes)}")
    print(f"\nHeader bytes (first 4):")
    for i in range(4):
        print(f"  Byte {i}: 0x{compiled1_bytes[i]:02X} ({compiled1_bytes[i]:3d})")

    # Try BOTH little-endian interpretations
    print("\n--- LENGTH FIELD INTERPRETATION ATTEMPTS ---")

    # Try 1: Bytes 2-3 as little-endian
    length_v1 = compiled1_bytes[2] | (compiled1_bytes[3] << 8)
    print(f"Attempt 1 (bytes [2:4] LE): 0x{compiled1_bytes[2]:02X}{compiled1_bytes[3]:02X} → {length_v1} decimal")

    # Try 2: Bytes 2-3 as big-endian
    length_v2 = (compiled1_bytes[2] << 8) | compiled1_bytes[3]
    print(f"Attempt 2 (bytes [2:4] BE): 0x{compiled1_bytes[2]:02X}{compiled1_bytes[3]:02X} → {length_v2} decimal")

    # Try 3: What if length is encoded differently?
    print(f"\nActual payload size (compiled - header): {len(compiled1_bytes) - 4}")
    print(f"Source data size: {len(source1_bytes)}")

    # AHA! What if the length is encoded with a flag byte?
    # 0x80 = 128 in decimal, but might be a flag + 7-bit value
    # Or could be variable-length encoding!

    print("\n--- ALTERNATIVE ENCODING HYPOTHESIS ---")
    if compiled1_bytes[2] & 0x80:
        print("Byte 2 has high bit set (0x80 & 0x80 = 0x80)")
        print("This might indicate a 2-byte length encoding!")

        # Variable-length integer encoding (common in binary formats)
        # High bit = 1 means "more bytes follow"
        byte2_value = compiled1_bytes[2] & 0x7F  # Clear high bit
        byte3_value = compiled1_bytes[3]

        # Try: (byte2_lower_7_bits) + (byte3 << 7)
        length_v3 = byte2_value | (byte3_value << 7)
        print(f"Variable-length encoding attempt: {length_v3} decimal")

        # Try: Just byte3 (byte2 is flag)
        length_v4 = byte3_value
        print(f"Byte 3 only: {length_v4} decimal")

    # Check payload match
    payload1 = compiled1_bytes[4:]
    print(f"\n--- PAYLOAD VERIFICATION ---")
    print(f"Payload bytes: {len(payload1)}")
    print(f"Source bytes: {len(source1_bytes)}")
    print(f"EXACT MATCH: {payload1 == bytes(source1_bytes)}")

    if payload1 == bytes(source1_bytes):
        print("\n*** CRITICAL FINDING: Payload IS the direct byte conversion! ***")
        print("*** The length field MUST encode 150 somehow ***")

    print("\n\n--- EXAMPLE 2 ANALYSIS ---")
    print(f"Source hex pairs: {len(source2_hex_pairs)}")
    print(f"Compiled total bytes: {len(compiled2_bytes)}")
    print(f"\nHeader bytes (first 4):")
    for i in range(4):
        print(f"  Byte {i}: 0x{compiled2_bytes[i]:02X} ({compiled2_bytes[i]:3d})")

    # Check if header is IDENTICAL to example 1
    if compiled1_bytes[:4] == compiled2_bytes[:4]:
        print("\n*** BREAKTHROUGH: HEADERS ARE IDENTICAL! ***")
        print("Both examples have same header: 05 0B 80 96")
        print("But they have DIFFERENT source data lengths!")
        print(f"  Example 1 payload: {len(compiled1_bytes) - 4} bytes")
        print(f"  Example 2 payload: {len(compiled2_bytes) - 4} bytes")
        print("\n==> Length field does NOT encode actual payload size!")
        print("==> It might be a MAXIMUM size or a format identifier!")

    payload2 = compiled2_bytes[4:]
    print(f"\n--- PAYLOAD VERIFICATION (Example 2) ---")
    print(f"Payload bytes: {len(payload2)}")
    print(f"Source bytes: {len(source2_bytes)}")

    # Check byte-by-byte comparison
    matches = 0
    for i in range(min(len(payload2), len(source2_bytes))):
        if payload2[i] == source2_bytes[i]:
            matches += 1

    print(f"Matching bytes: {matches} / {min(len(payload2), len(source2_bytes))}")

    if matches != min(len(payload2), len(source2_bytes)):
        print("\n--- MISMATCH ANALYSIS ---")
        print("First 20 payload bytes:", ' '.join(f'{b:02X}' for b in payload2[:20]))
        print("First 20 source bytes: ", ' '.join(f'{b:02X}' for b in source2_bytes[:20]))

        # Find where they diverge
        for i in range(min(len(payload2), len(source2_bytes))):
            if payload2[i] != source2_bytes[i]:
                print(f"\nFirst mismatch at offset {i}:")
                print(f"  Payload: 0x{payload2[i]:02X}")
                print(f"  Source:  0x{source2_bytes[i]:02X}")
                break

    print("\n" + "=" * 80)
    print("HYPOTHESIS REFINEMENT")
    print("=" * 80)
    print("""
Based on the analysis:

1. OPCODE = 0x05 (constant for idb_append_data)
2. SUBOPCODE/FLAGS = 0x0B (constant, purpose unknown)
3. LENGTH FIELD = 0x80 0x96 (constant in BOTH examples!)
   - Does NOT represent actual payload length
   - Likely a format marker, protocol version, or maximum size
   - Value: 0x9680 (little-endian) = 38528
   - This might be the MAXIMUM buffer size, not actual length!

4. PAYLOAD = Direct byte conversion from hex pairs
   - Actual length is IMPLICIT (read until frame end)
   - Or length is encoded at a HIGHER protocol layer (P3 frames?)

CONCLUSION: This is a LENGTH-LESS encoding!
The P3 frame or parent structure must provide the actual length.
The 0x9680 is likely a type identifier or max buffer constant.
    """)

if __name__ == '__main__':
    analyze_hex_data_v2()
