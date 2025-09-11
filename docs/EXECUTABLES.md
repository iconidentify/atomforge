# Available Executables

## Primary Tools

### `bin/ada32_compiler.exe`
**Source**: `src/production/ada32_compiler.c`  
**Purpose**: Main Ada32.dll compiler - converts .txt atom stream files to binary .bin/.str files  
**Usage**: `cd bin/runtime && wine ../ada32_compiler.exe input.txt output.bin`  
**Output**: Complete binary files (413-649 bytes depending on input)  

## Diagnostic Tools

### `bin/ada32_diagnostic.exe`
**Source**: `src/analysis/ada32_diagnostic.c`  
**Purpose**: Tests basic Ada32.dll functionality with known good file  
**Usage**: `cd bin/runtime && wine ../ada32_diagnostic.exe`  
**Output**: Validates Ada32.dll is working and produces expected 413-byte output  

### `bin/ada32_debugger.exe`
**Source**: `src/analysis/ada32_debugger.c`  
**Purpose**: Debug compilation issues and troubleshoot Ada32.dll problems  
**Usage**: `cd bin/runtime && wine ../ada32_debugger.exe`  
**Output**: Detailed debugging information for troubleshooting  

## Automation

### `scripts/compile_all_golden_tests.py`
**Purpose**: Batch compilation of all 33 golden test files  
**Usage**: `python3 scripts/compile_all_golden_tests.py`  
**Features**: 
- Automatic special character encoding (& → 26x)
- GID header removal
- Error reporting and progress tracking

## Requirements

All executables require:
- Runtime files in `bin/runtime/`: Ada32.dll, GIDINFO.INF, Ada.bin
- Wine emulation environment (Docker container provided)
- Must be run from `bin/runtime/` directory for DLL loading

## Building

To rebuild executables:
```bash
# Main compiler
i686-w64-mingw32-gcc -o bin/ada32_compiler.exe src/production/ada32_compiler.c

# Diagnostic tools
i686-w64-mingw32-gcc -o bin/ada32_diagnostic.exe src/analysis/ada32_diagnostic.c
i686-w64-mingw32-gcc -o bin/ada32_debugger.exe src/analysis/ada32_debugger.c
```

## Docker Integration

The `bin/runtime/` directory is mounted as the working directory in Docker:
```bash
docker run --rm \
  -v $(pwd):/workspace \
  -v $(pwd)/bin/runtime:/workspace/runtime \
  ada32_toolkit-ada32-wine bash -c \
  "cd /workspace/runtime && wine ../ada32_compiler.exe ../input.txt ../output.bin"
```