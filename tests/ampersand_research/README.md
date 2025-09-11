# Ampersand Character Research

## Problem Discovery

During compilation of golden test file `32-2271.txt`, we discovered that Ada32.dll crashes when processing ampersand (`&`) characters in token parameters.

## Root Cause

The issue occurs specifically with `sm_send_token_arg` parameters containing ampersands:

```
sm_send_token_arg <L&>  // ❌ Causes Wine exception 0x80000003 at address 100045B5
```

## Solution

Ada32.dll supports hex encoding for special characters using the `<XXx>` format:

```  
sm_send_token_arg <L26x>  // ✅ Works (26 = hex value of &)
```

## Test Results

| Test Case | Input | Result | Notes |
|-----------|-------|--------|-------|
| `test_l_amp.txt` | `<L&>` | ❌ Crash | Original problematic case |
| `test_hex_amp.txt` | `<L26x>` | ✅ Success | Hex encoding solution |
| `test_a_amp.txt` | `<A&>` | ❌ Crash | Confirms any & character crashes |
| `test_just_amp.txt` | `<&>` | ❌ Crash | Even standalone & crashes |

## Key Files

- `test_hex_amp.txt` - Minimal working example with hex encoding
- `test_hex_amp.bin` - 13-byte successful compilation output  
- `temp_32_2271_hex.txt` - Full 32-2271.txt with hex-encoded ampersand
- `test_32_2271_hex.bin` - 649-byte successful compilation of full file

## Implementation

The solution is implemented in `scripts/compile_all_golden_tests.py` with the `hex_encode_special_chars()` function that automatically converts `&` → `26x` in token parameters while preserving original files.

## Reference

- `golden_tests_immutable/32-2271.str` (485 bytes) - Reference file containing properly compiled `L&` token
- Binary contains `4c 4c 26` sequence which confirms the `L&` token was successfully processed