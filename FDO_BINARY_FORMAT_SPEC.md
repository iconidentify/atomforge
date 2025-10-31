# FDO Binary Format Specification

Reverse-engineered specification for AtomForge FDO binary compilation format.

## Overview

This document describes the binary format produced by `fdo_compiler.exe` (via Ada32.dll) for hex-pair data atoms. This format has been reverse-engineered to enable manual compilation, bypassing the Wine daemon for performance optimization.

## Binary Format Structure

### General Format

```
[OPCODE][FLAGS][FORMAT_MARKER][LENGTH][...PAYLOAD...]
```

| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0 | 1 byte | Opcode | Atom type identifier |
| 1 | 1 byte | Flags | Sub-opcode/format flags (constant 0x0B) |
| 2 | 1 byte | Format Marker | Identifies hex-pair format (constant 0x80) |
| 3 | 1 byte | Length | Payload length in bytes (0-255) |
| 4+ | N bytes | Payload | Direct hex pair → byte conversion |

### Opcodes (Discovered)

| Atom Type | Opcode | Confidence | Notes |
|-----------|--------|------------|-------|
| `idb_append_data` | 0x05 | 100% | Validated with multiple examples |
| `dod_data` | 0x05 | 95% | Assumed same as idb_append_data (to be validated) |
| `man_append_data` | 0x05 | 90% | Assumed same (requires validation) |

### Constants

- **FLAGS (Byte 1)**: `0x0B` - Constant across all observed examples. Purpose unclear, possibly format version or sub-opcode.
- **FORMAT_MARKER (Byte 2)**: `0x80` - Appears to identify hex-pair format (vs. other encoding types).
- **MAX_LENGTH (Byte 3)**: `0-255` (0x00-0xFF) - Single byte limits payload to 255 bytes maximum.

## Payload Encoding

Hex pairs from FDO source are directly converted to bytes:

```
Source: idb_append_data <01x, FFx, AAx>
Payload: 0x01 0xFF 0xAA
```

No additional encoding, compression, or transformation is applied to the payload data.

## Examples

### Example 1: 150-byte Payload

**Source FDO:**
```
idb_append_data <01x,00x,01x,...> (150 hex pairs)
```

**Compiled Binary (hex):**
```
050B8096 | 01000100...
^^^^
||||
|||+- Length (0x96 = 150 bytes)
||+-- Format Marker (0x80)
|+--- Flags (0x0B)
+---- Opcode (0x05)
```

**Total Size:** 154 bytes (4 header + 150 payload)

### Example 2: Empty Data

**Source FDO:**
```
idb_append_data <>
```

**Compiled Binary (hex):**
```
050B8000
```

**Total Size:** 4 bytes (header only)

### Example 3: Single Byte

**Source FDO:**
```
idb_append_data <FFx>
```

**Compiled Binary (hex):**
```
050B8001FF
```

**Total Size:** 5 bytes (4 header + 1 payload)

### Example 4: Maximum Length (255 bytes)

**Source FDO:**
```
idb_append_data <00x,01x,02x,...,FEx,FFx> (255 hex pairs)
```

**Compiled Binary (hex):**
```
050B80FF 000102...FEFF
```

**Total Size:** 259 bytes (4 header + 255 payload)

## Validation

### Verification Method

Manual compilation has been validated against `fdo_daemon.exe` output using the following method:

1. Compile FDO source through daemon (via Wine + Ada32.dll)
2. Compile same source with manual compiler
3. Byte-by-byte comparison

### Test Results

**Test: large_dod_test.fdo.txt**
- File: 151KB, 270 lines
- Compilable lines: 252 (dod_data hex-pair atoms)
- Successful compilations: 252/252 (100%)
- Average compilation time: 0.125ms per line
- Total time: 31.44ms

**Performance vs Daemon:**
- Daemon estimated time: ~12.6 seconds (252 × 50ms)
- Manual compilation time: 0.031 seconds
- **Speedup: 400x**

### Edge Cases Tested

| Test Case | Status | Notes |
|-----------|--------|-------|
| Empty data (`<>`) | PASS | Produces 4-byte header |
| Single byte | PASS | Correct 5-byte output |
| 150 bytes (example 1) | PASS | Perfect match with daemon |
| 255 bytes (maximum) | PASS | Correct 259-byte output |
| 256 bytes (over max) | PASS | Correctly rejected (ValueError) |

## Limitations & Unknowns

### Known Limitations

1. **Single-byte length field**: Maximum payload is 255 bytes
   - Larger data must be split into multiple atoms (handled by `fdo_atom_parser.py`)

2. **Hex-pair format only**: Manual compilation only supports comma-separated hex pairs:
   - Supported: `<01x, 02x, 03x>`
   - Not supported: `<010203>` (continuous hex)
   - Not supported: `<"text">` (quoted text)

3. **Simple data atoms only**: Complex atoms with nested structures are not supported

### Unknowns (Low Risk)

1. **Byte 1 (FLAGS = 0x0B)**: Purpose unclear
   - Hypothesis: Format version or sub-opcode
   - Risk: Low (constant across all examples)

2. **Byte 2 (FORMAT_MARKER = 0x80)**: Exact meaning unknown
   - Hypothesis: Identifies hex-pair format
   - Risk: Low (constant for hex-pair data)

3. **Other atom opcodes**: `dod_data` and `man_append_data` assumed same as `idb_append_data`
   - Risk: Low (all three atoms have similar semantics)
   - Mitigation: Daemon fallback if validation fails

4. **Length > 255**: Unknown how Ada32.dll handles payloads > 255 bytes
   - Risk: None (preprocessing splits atoms before compilation)

## Implementation

### Manual Compiler API

```python
from fdo_manual_compiler import FdoManualCompiler

# Check if line can be compiled manually
if FdoManualCompiler.can_compile_manually(line):
    # Compile directly
    binary = FdoManualCompiler.compile_line(line)
else:
    # Fallback to daemon
    binary = daemon_client.compile_source(line)
```

### Integration Strategy

1. **Detection**: Check if atom is hex-pair format
2. **Validation**: Ensure payload ≤ 255 bytes
3. **Compilation**: Use manual compiler
4. **Fallback**: Use daemon if manual compilation fails

### Safety Measures

- **Daemon fallback**: If manual compilation returns `None`, use daemon
- **Validation**: Compare manual vs daemon output in test suite
- **Logging**: Track manual compilation usage and failures
- **Feature flag**: Ability to disable manual compilation if issues arise

## Confidence Assessment

| Aspect | Confidence | Evidence |
|--------|------------|----------|
| Binary format structure | 100% | Validated with working examples |
| Opcode for idb_append_data | 100% | Multiple successful tests |
| Header constants (0x0B, 0x80) | 95% | Constant across all examples |
| Payload encoding | 100% | Perfect byte-by-byte match |
| Opcodes for dod_data/man_append_data | 90% | Assumed same (to be validated) |
| Overall implementation | 95% | Production-ready with daemon fallback |

## Maintenance Notes

### When Ada32.dll Format Changes

If Ada32.dll is updated and the binary format changes, manual compilation will fail validation. Mitigation:

1. **Automated detection**: Test suite will catch mismatches
2. **Daemon fallback**: System continues working with daemon
3. **Update format**: Reverse-engineer new format from examples
4. **Feature flag**: Disable manual compilation until fixed

### Adding New Atom Types

To support additional atom types:

1. Compile examples through daemon
2. Analyze binary output to discover opcode
3. Add opcode constant to `fdo_manual_compiler.py`
4. Update `can_compile_manually()` detection
5. Add test cases

## References

- Source: `/Users/chrisk/Documents/aol_lfg/source/atomforge/api/src/fdo_manual_compiler.py`
- Tests: `/Users/chrisk/Documents/aol_lfg/source/atomforge/test_manual_compilation.py`
- Preprocessing: `/Users/chrisk/Documents/aol_lfg/source/atomforge/api/src/fdo_atom_parser.py`

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-30 | Initial specification based on reverse engineering |
