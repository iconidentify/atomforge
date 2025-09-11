# Automation Scripts

## `compile_all_golden_tests.py`

**Purpose**: Automated compilation of all 33 golden test files using Ada32.dll

**Features**:
- Processes all `.txt` files in `golden_tests_immutable/`
- Automatic GID header removal
- Hex encoding for special characters (`&` → `26x`)
- Generates `.program.output.bin` files for analysis
- Comprehensive error reporting and progress tracking

**Usage**:
```bash
python3 scripts/compile_all_golden_tests.py
```

**Requirements**:
- `bin/runtime/` directory with Ada32.dll and support files
- Docker environment with ada32_toolkit-ada32-wine image
- All golden test files in `golden_tests_immutable/`

**Output**: 
- Creates `.program.output.bin` files next to each `.txt` file
- Binary files range from 24 bytes to 2,030 bytes
- 100% success rate across all 33 golden test files

**Special Character Handling**:
The script automatically handles problematic characters in token parameters:
- Detects `&` characters in `<token_parameters>`
- Converts to hex encoding (`&` → `26x`)
- Preserves original files unchanged
- Only affects token parameters, not string literals

**Example Output**:
```
🚀 Compiling All Golden Tests with Restored Ada32.dll
=======================================================
📁 Found 33 golden test files

🔄 Compiling 32-105.txt...
   ✅ Success: 413 bytes -> golden_tests_immutable/32-105.program.output.bin
🔄 Compiling 32-106.txt...
   ✅ Success: 272 bytes -> golden_tests_immutable/32-106.program.output.bin
...

📊 Compilation Summary
====================
✅ Successful: 33
❌ Failed: 0
📁 Total: 33
```