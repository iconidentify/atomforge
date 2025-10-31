#!/usr/bin/env python3
"""
Deep dive into the compiled format - checking if example 2 is a continuation.
"""

def deep_dive_analysis():
    """Check if the examples are part of a sequence."""

    # Example 1 - FULL
    source1_full = """idb_append_data <01x,00x,01x,00x,01x,00x,0bx,05x,00x,00x,01x,00x,00x,00x,05x,02x,78x,00x,29x,00x,00x,00x,e7x,04x,00x,00x,24x,00x,00x,00x,00x,00x,00x,00x,00x,00x,80x,fdx,00x,00x,47x,49x,46x,38x,37x,61x,78x,00x,29x,00x,d5x,00x,00x,00x,00x,00x,ffx,00x,00x,ffx,80x,00x,ffx,80x,40x,ffx,8ex,1cx,edx,92x,24x,f7x,99x,2bx,fcx,9dx,2cx,fcx,9fx,31x,ffx,9fx,20x,fcx,a1x,34x,ffx,a2x,2fx,fcx,a4x,3cx,ffx,a4x,24x,fcx,a7x,42x,fcx,a8x,44x,ffx,aax,00x,ffx,aax,2bx,ffx,aax,39x,fcx,acx,4cx,fcx,afx,53x,fcx,b0x,56x,fcx,b3x,5bx,fdx,b6x,63x,ffx,b6x,24x,fdx,b8x,66x,fdx,bax,6ax,fdx,bex,73x,fdx,c0x,77x,fdx,c2x,7cx,fdx,c6x,84x,fdx,c7x,88x,fdx>"""

    compiled1_hex = "050B80960100010001000B050000010000000502780029000000E70400002400000000000000000080FD000047494638376178002900D50000000000FF0000FF8000FF8040FF8E1CED9224F7992BFC9D2CFC9F31FF9F20FCA134FFA22FFCA43CFFA424FCA742FCA844FFAA00FFAA2BFFAA39FCAC4CFCAF53FCB056FCB35BFDB663FFB624FDB866FDBA6AFDBE73FDC077FDC27CFDC684FDC788FD"

    # Example 2 - Might be continuation
    source2_full = """idb_append_data <c9x,8bx,fdx,cdx,93x,fdx,d1x,9dx,fdx,d4x,a4x,fdx,d7x,a9x,fdx,d9x,aex,fdx,dcx,b4x,fdx,dex,bax,fdx,e0x,bex,fdx,e3x,c4x,fex,e6x,cbx,fex,e8x,cex,fex,eax,d3x,fex,eex,dcx,fex,f0x,dfx,fex,f1x,e3x,fex,f5x,ebx,fex,f7x,f0x,fex,f9x,f4x,ffx,ffx,00x,ffx,ffx,ffx,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,21x,f9x,04x,09x,00x,00x,35x,00x,2cx,00x,00x,00x,00x,78x,00x,29x,00x,00x,06x,ffx,c0x,9ax,70x,38x,3cx,18x,8fx,c8x,a4x,72x,c9x,6cx,3ax,9fx,d0x,a8x,93x,48x,adx,d6x,a4x,d8x,acx,76x,cbx,65x,5ax,89x,ddx,b0x,78x,4cx,fex,5ex,c9x>"""

    compiled2_hex = "050B8096C98BFDCD93FDD19DFDD4A4FDD7A9FDD9AEFDDCB4FDDEBAFDE0BEFDE3C4FEE6CBFEE8CEFEEAD3FEEEDCFEF0DFFEF1E3FEF5EBFEF7F0FEF9F4FFFF00FFFFFF00000000000000000000000000000000000000000000000000000000000021F90409000035002C00000000780029000006FFC09A70383C188FC8A472C96C3A9FD0A89348ADD6A4D8AC76CB655A89DDB0784CFE5EC9"

    print("=" * 80)
    print("DEEP DIVE: Are these examples connected?")
    print("=" * 80)

    # Parse hex pairs from source
    import re
    def extract_hex_pairs(source_text):
        matches = re.findall(r'([0-9a-fA-F]+)x', source_text)
        return [int(h, 16) for h in matches]

    source1_bytes = extract_hex_pairs(source1_full)
    source2_bytes = extract_hex_pairs(source2_full)

    compiled1_bytes = bytes.fromhex(compiled1_hex)
    compiled2_bytes = bytes.fromhex(compiled2_hex)

    print(f"\nExample 1: {len(source1_bytes)} hex pairs → {len(compiled1_bytes)} compiled bytes")
    print(f"Example 2: {len(source2_bytes)} hex pairs → {len(compiled2_bytes)} compiled bytes")

    # Check if headers are identical
    header1 = compiled1_bytes[:4]
    header2 = compiled2_bytes[:4]

    print(f"\nHeader 1: {header1.hex().upper()}")
    print(f"Header 2: {header2.hex().upper()}")
    print(f"Headers identical: {header1 == header2}")

    # Wait... byte 3 is 0x96 = 150 decimal
    # Both examples have 150 source hex pairs!
    print(f"\n*** INSIGHT: Byte 3 = 0x96 = {0x96} decimal ***")
    print(f"Example 1 has {len(source1_bytes)} hex pairs")
    print(f"Example 2 has {len(source2_bytes)} hex pairs")
    print(f"\nBoth examples have EXACTLY 150 source hex pairs!")
    print(f"==> Byte 3 (0x96) IS the payload length!")

    # So what is byte 2 (0x80)?
    print(f"\n--- DECODING BYTE 2 (0x80) ---")
    print(f"0x80 = {0x80} decimal = {0x80:08b} binary")
    print(f"High bit set = flag for multi-byte length? Or opcode variant?")

    # Check the actual payload
    payload1 = compiled1_bytes[4:]
    payload2 = compiled2_bytes[4:]

    print(f"\n--- PAYLOAD COMPARISON ---")
    print(f"Payload 1 length: {len(payload1)}")
    print(f"Payload 2 length: {len(payload2)}")
    print(f"Source 1 length: {len(source1_bytes)}")
    print(f"Source 2 length: {len(source2_bytes)}")

    # Verify exact match for example 1
    if payload1 == bytes(source1_bytes):
        print(f"\nExample 1: EXACT MATCH (payload == source bytes)")
    else:
        print(f"\nExample 1: MISMATCH")

    # Check example 2 more carefully
    print(f"\n--- EXAMPLE 2 DETAILED CHECK ---")
    print(f"Expected payload length: {len(source2_bytes)}")
    print(f"Actual payload length: {len(payload2)}")
    print(f"Difference: {len(source2_bytes) - len(payload2)} bytes")

    # Maybe the compiled output is TRUNCATED in the user's example?
    # Or maybe there's a NULL terminator or delimiter?

    # Check byte-by-byte
    print(f"\nByte-by-byte comparison (first 20):")
    for i in range(min(20, len(payload2), len(source2_bytes))):
        match = "✓" if payload2[i] == source2_bytes[i] else "✗"
        print(f"  [{i:2d}] Payload: 0x{payload2[i]:02X}  Source: 0x{source2_bytes[i]:02X}  {match}")

    # Find the exact divergence point
    print(f"\nFinding divergence point...")
    for i in range(min(len(payload2), len(source2_bytes))):
        if payload2[i] != source2_bytes[i]:
            print(f"First mismatch at byte {i}:")
            print(f"  Payload[{i}] = 0x{payload2[i]:02X}")
            print(f"  Source[{i}]  = 0x{source2_bytes[i]:02X}")

            # Show context
            print(f"\n  Context (payload):")
            start = max(0, i-5)
            end = min(len(payload2), i+6)
            print(f"    {' '.join(f'{b:02X}' for b in payload2[start:end])}")
            print(f"                  ^^")

            print(f"\n  Context (source):")
            print(f"    {' '.join(f'{b:02X}' for b in source2_bytes[start:end])}")
            print(f"                  ^^")
            break
    else:
        # No mismatch in overlapping region - check if one is longer
        if len(payload2) < len(source2_bytes):
            print(f"\nPayload is SHORTER than source by {len(source2_bytes) - len(payload2)} bytes")
            print(f"Missing bytes: {' '.join(f'{b:02X}' for b in source2_bytes[len(payload2):])}")
        elif len(payload2) > len(source2_bytes):
            print(f"\nPayload is LONGER than source by {len(payload2) - len(source2_bytes)} bytes")
            print(f"Extra bytes: {' '.join(f'{b:02X}' for b in payload2[len(source2_bytes):])}")
        else:
            print(f"\nEXACT MATCH!")

    print("\n" + "=" * 80)
    print("REFINED FORMAT SPECIFICATION")
    print("=" * 80)
    print("""
Based on analysis:

Structure: [OPCODE][FLAGS][??][LENGTH][...PAYLOAD...]

Byte 0: 0x05 - OPCODE for idb_append_data
Byte 1: 0x0B - FLAGS or sub-opcode (purpose TBD)
Byte 2: 0x80 - Unknown (flag? high byte of length? format marker?)
Byte 3: 0x96 - LENGTH of payload in bytes (150 decimal)
Bytes 4+: Direct byte conversion from hex pairs

KEY INSIGHT: Both examples have 150 source hex pairs, and byte 3 = 0x96 = 150!
This strongly suggests byte 3 IS the length field.

REMAINING QUESTION: What is byte 2 (0x80)?
  - Possible: High byte of 16-bit length (allowing up to 65535 bytes)
  - Possible: Format flag (0x80 = hex-pair format vs other formats?)
  - Possible: Opcode extension or variant marker
    """)

if __name__ == '__main__':
    deep_dive_analysis()
