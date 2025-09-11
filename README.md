# AOL Ada32 Toolkit

A comprehensive toolkit for working with AOL's Ada32.dll atom stream compilation system.

## Overview

This project provides tools and research for converting AOL atom stream text files (.txt) to binary stream files (.str) using the original Ada32.dll functions. We have successfully restored full Ada32.dll compilation functionality with **100% success rate** across all golden test files, producing binary outputs ranging from 24 bytes to 2,030 bytes.

## Repository Structure

```
ada32_toolkit/
├── bin/                    # Built executables and runtime files
│   ├── runtime/           # DLLs and support files (mounted in Docker)
│   ├── dlls/              # Archived DLL versions
│   └── executables/       # Legacy executable archive
├── src/                   # Source code (C programs)
│   ├── production/        # Working, production-ready code
│   ├── research/          # Experimental research code (57 files)
│   └── analysis/          # Binary analysis and format tools
├── scripts/               # Automation scripts
├── research/              # Python research scripts
│   └── python/           # 20+ Python analysis and encoding scripts
├── research_materials/   # Original reference implementations and research materials
├── tests/                 # Test data and archived outputs
│   ├── fixtures/          # Test input files
│   └── output_archive/    # Historical test outputs (106 files)
├── docs/                  # Documentation
├── golden_tests_immutable/ # Reference data (DO NOT MODIFY)
├── build_tools/           # Docker, build scripts, configuration
└── docker-compose.yml     # Development environment
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Compiling Golden Test Files

**Compile all 33 golden test files:**
```bash
python3 scripts/compile_all_golden_tests.py
```

This generates `.program.output.bin` files for all golden test files with automatic special character handling.

**Compile a single file:**
```bash
docker run --rm \
  -v $(pwd):/workspace \
  -v $(pwd)/bin/runtime:/workspace/runtime \
  ada32_toolkit-ada32-wine bash -c \
  "cd /workspace/runtime && wine ../bin/ada32_compiler.exe ../input.txt ../output.bin"
```

### Manual Compilation Setup

1. **Start the development environment:**
   ```bash
   docker-compose run --rm ada32-wine bash
   ```

2. **Compile the main compiler:**
   ```bash
   cd /ada32_toolkit
   i686-w64-mingw32-gcc -o bin/ada32_compiler.exe src/production/ada32_compiler.c
   ```

3. **Runtime files are organized in bin/runtime/:**
   ```bash
   # Ada32.dll and supporting files are in bin/runtime/
   ls bin/runtime/  # Shows: Ada32.dll, Ada.bin, GIDINFO.INF, etc.
   ```

## Current Capabilities

### ✅ Working Features
- **100% Golden Test Success** - All 33 golden test files compile successfully  
- **Ada32.dll Fully Restored** - Complete AdaAssembleAtomStream() functionality
- **Special Character Handling** - Automatic hex encoding for problematic characters
- **Supporting File Detection** - Automatic setup of required GIDINFO.INF and Ada.bin
- **Automated Compilation Suite** - Python wrapper for batch processing
- **Cross-platform development** - Works on macOS/Linux via Docker + Wine
- **Comprehensive Documentation** - All discoveries and workarounds documented

### 🔧 Technical Achievements
- **Required Dependencies Identified**: Ada32.dll needs GIDINFO.INF and Ada.bin support files
- **Special Character Encoding**: Ampersands in token parameters must use hex format (`&` → `26x`)
- **Flexible Compiler**: Handles any input file with proper error reporting
- **Binary Output Range**: 24 bytes to 2,030 bytes depending on input complexity

### ⚠️ Known Limitations  
- **Ampersand Token Bug**: Raw `&` characters in `sm_send_token_arg` parameters crash Ada32.dll
  - **Workaround**: Automatic hex encoding (`L&` → `L26x`) in compilation pipeline
- **Database functions** - Dbaol32.dll functions crash in current environment

## File Formats

### Input Format (.txt)
Text-based atom stream format:
```
uni_start_stream <00x>
  man_start_object <independent, "Public Rooms in People Connection">
  ...
```

### Output Format (.program.output.bin)
Binary compiled atom streams with sizes ranging from 24 bytes to 2,030 bytes. Each golden test file now has a corresponding compiled binary output for analysis.

### Special Character Handling

Ada32.dll requires specific formatting for special characters in token parameters:

**Problem**: Direct ampersand usage causes crashes
```
sm_send_token_arg <L&>  // ❌ Causes Wine exception 0x80000003
```

**Solution**: Hex encoding using `<XXx>` format  
```
sm_send_token_arg <L26x>  // ✅ Works (26 = hex value of &)
```

**Implementation**: The compilation pipeline automatically converts special characters:
- Detects `&` characters within `<token_parameters>`
- Converts to hex format (`&` → `26x`)
- Preserves original files unchanged
- Only affects token parameters, not string literals like `"Help & Info"`

**Reference Files**: 
- `golden_tests_immutable/32-2271.str` - Contains properly compiled `L&` token
- `Ada.bin` - Token definition file containing `sm_send_token_arg` and variants

## Key Files

### Production Code
- `src/production/ada32_compiler.c` - **Primary compiler** - Handles any input file with proper error reporting
- `scripts/compile_all_golden_tests.py` - **Automated compilation suite** - Processes all golden tests with special character handling
- `src/production/ada32_production_test.c` - Legacy compiler implementation
- `src/production/simple_compiler.c` - Simplified compiler variant

### Research Code
- `src/research/test_refined_chaining.c` - Advanced function chaining experiments
- `src/research/test_reverse_chaining.c` - Alternative compilation approaches

### Analysis Tools
- `src/analysis/ada32_diagnostic.c` - **Diagnostic tool** - Tests basic Ada32.dll functionality
- `src/analysis/ada32_debugger.c` - **Debug tool** - Troubleshoots compilation issues  
- `src/analysis/analyze_format_differences.c` - Binary format comparison
- `src/analysis/analyze_ada32_output.c` - Output analysis tool
- `src/analysis/analyze_normalize_function.c` - Function analysis
- `src/analysis/debug_db_functions.c` - Database function debugging

### Reference Data
- `golden_tests_immutable/*.txt` - **33 immutable golden test files** (NEVER MODIFY)
- `golden_tests_immutable/*.str` - **Reference binary outputs** (various sizes)
- `golden_tests_immutable/*.program.output.bin` - **Generated compilation outputs** (24-2030 bytes)
- `tests/fixtures/clean_32-105.txt` - Working input file for testing

### Supporting Files (Required for Ada32.dll)
- `bin/runtime/GIDINFO.INF` - DLL configuration file (25 bytes)
- `bin/runtime/Ada.bin` - Token definition file (121,020 bytes) containing function names like `sm_send_token_arg`
- `bin/runtime/Ada32.dll` - Main compilation DLL (239,104 bytes)
- `bin/runtime/Dbaol32.dll` - Database functions DLL (25,600 bytes)

### Research Materials
- `research_materials/star_tool/` - STAR tool with Ada32.dll v1 (103KB, 1999)
- `research_materials/dbviewer_original/` - DBViewer with Ada32.dll v2 (239KB, 1997)
- `research_materials/Ada32_exports.json` - Function exports for Ada32.dll v2
- `research_materials/README.md` - Documentation of research materials

## Development

### Environment Setup
The project uses Docker with Wine emulation to run Windows DLLs on Linux/macOS:

```bash
# Start development environment
docker-compose run --rm ada32-wine bash

# Compile Windows executable
i686-w64-mingw32-gcc -o output.exe source.c

# Run with Wine
wine output.exe
```

### Testing
Test fixtures are located in `tests/fixtures/` and should not be modified. All test outputs are archived in `tests/output_archive/` for historical reference.

## Documentation

- **[Research Findings](docs/RESEARCH_FINDINGS.md)** - Comprehensive analysis of Ada32.dll and related DLLs
- **[Golden Tests README](golden_tests_immutable/README.md)** - Information about immutable reference data

## Contributing

When working on this project:

1. **Test data is immutable** - Never modify files in `golden_tests_immutable/`
2. **Archive outputs** - Save test results to `tests/output_archive/` with descriptive names
3. **Document findings** - Update `docs/RESEARCH_FINDINGS.md` with new discoveries
4. **Preserve functionality** - Ensure the 413-byte compilation capability is maintained

## License

This project is for educational and research purposes, working with legacy AOL software components.