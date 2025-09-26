# AtomForge Backend

Field Data Object processing backend for the AtomForge web application. Provides HTTP API and command-line utilities for compiling and decompiling Field Data Objects (FDO) used in AOL Database systems.

## Overview

AtomForge Backend provides three main utilities:

* fdo_compiler.exe - Compiles human-readable FDO source files into binary format
* fdo_decompiler.exe - Decompiles binary FDO files back to human-readable source
* fdo_daemon.exe - HTTP daemon providing REST API for compile/decompile operations

These tools interface with the Ada32.dll library to provide professional-grade FDO processing capabilities for reverse engineering, analysis, and development of AOL Database applications.

## System Requirements

### Runtime Dependencies

* Wine - Required for running Windows executables on Linux
* Ada32.dll - Core FDO processing library
* SUPERSUB.DLL - Required dependency for Ada32.dll
* Ada.bin - Runtime data file
* Visual C++ 6.0 Runtime - mfc42.dll, mfc42u.dll, msvcp60.dll, msvcrt.dll

### Build Dependencies

* GCC/MinGW cross-compiler (mingw-w64 package)
* CMake 3.16 or later
* Make
* Wine (for testing executables)

## Installation

### Prerequisites

Ubuntu/Debian:
```
sudo apt update
sudo apt install build-essential cmake wine mingw-w64
```

Red Hat/CentOS:
```
sudo yum groupinstall "Development Tools"
sudo yum install cmake wine mingw64-gcc
```

### Build

```
git clone <repository>
cd atomforge-backend
make
```

### Test

```
make test
```

## Usage

### Command Line Tools

Compile FDO source to binary:
```
cd build/bin
wine fdo_compiler.exe input.txt output.bin
```

Decompile binary back to source:
```
cd build/bin
wine fdo_decompiler.exe input.bin output.txt
```

### HTTP Daemon

Start daemon on port 8080:
```
cd build/bin
wine fdo_daemon.exe --port 8080
```

Compile via HTTP POST:
```
curl -X POST -H "Content-Type: text/plain" --data-binary "@input.txt" http://localhost:8080/compile -o output.bin
```

Decompile via HTTP POST:
```
curl -X POST -H "Content-Type: application/octet-stream" --data-binary "@input.bin" http://localhost:8080/decompile -o output.txt
```

Check daemon health:
```
curl http://localhost:8080/health
```

## Enhanced Error Handling

The HTTP API provides high-fidelity error reporting with structured JSON responses:

```json
{
  "error": {
    "message": "Ada32 error rc=0x2F0006: Missing Quote",
    "code": "0x2F0006",
    "line": 15,
    "column": 23,
    "kind": "Missing Quote",
    "context": [
      "  13 | uni_start_stream <00x>",
      "  14 |   man_start_object <independent, \"Object Name>",
      ">>15 |     mat_object_id <32-105",
      "  16 |     mat_orientation <vcf>",
      "  17 |   man_end_object"
    ],
    "hint": "unmatched quote — check for odd # of '\"' on this line or a missing closing quote across lines."
  }
}
```

**HTTP Status Code Mapping:**
- `400 Bad Request` - Syntax errors with line/column information
- `422 Unprocessable Entity` - Semantic errors in valid syntax
- `500 Internal Server Error` - System errors and API failures

## Sample Files

The `samples/` directory includes representative FDO files for testing and integration:

- **Valid Examples**: Demonstrate various FDO patterns and complexity levels
- **Error Examples**: Test error handling with known syntax issues
- **Performance Tests**: Files suitable for load and performance testing

Use these samples to validate your integration and test error handling capabilities.

See `samples/README_SAMPLES.md` for detailed information about each sample file.

## Build System

### Standard Targets

```
make                    # Build all executables
make clean              # Clean build directory
make test               # Run golden test suite
make check              # Build and test

make compiler           # Build compiler only
make decompiler         # Build decompiler only
make daemon             # Build daemon only

make debug              # Debug build with symbols
make release            # Optimized release build

make configure          # Configure CMake build manually
```

### Test Targets

```
make test               # Run CLI golden tests (streaming output)
make test-verbose       # Run tests with detailed failure analysis
make test-diff          # Run tests with diff analysis for failures
make test-daemon        # Run daemon golden tests
make test-daemon-verbose # Run daemon tests with verbose output
make test-all           # Run all tests (CLI + daemon)
make test-performance   # Run CLI tests with performance timing
make compare-performance # Compare CLI vs daemon performance
make stress-test        # Run 60-minute daemon stress test
```

## Testing

The project includes a comprehensive golden test suite with 252 real-world FDO samples from production AOL systems:

* 251 compile test files (.txt source format)
* 251 decompile test files (.str binary format from AOL .IDX database)

Test scripts automatically handle Wine environment detection and provide detailed error reporting with ASCII table output.

## Project Structure

```
atomforge-backend/
├── src/                    # Source code
│   ├── fdo_compiler/      # Compiler implementation
│   ├── fdo_decompiler/    # Decompiler implementation
│   ├── fdo_daemon/        # HTTP daemon implementation
│   └── shared/            # Common FDO processing code
├── runtime/               # Windows DLL dependencies
├── tests/                 # Golden test suite and scripts
│   ├── golden/           # 252 test cases (.txt and .str files)
│   └── scripts/          # Test automation scripts
├── cmake/                # CMake toolchain configuration
├── docs/                 # Documentation
├── build/                # Build output directory
│   └── bin/              # Compiled executables and runtime files
├── CMakeLists.txt        # CMake build configuration
└── Makefile              # Traditional make interface
```

## Technical Details

### Cross-Platform Architecture

* Native Linux build environment using CMake and MinGW cross-compilation
* Windows executable output (.exe files) with static libgcc/libstdc++ linking
* Wine runtime integration for Linux execution
* Comprehensive Windows API and DLL loading support

### Ada32.dll Integration

* Dynamic loading of Ada32.dll at runtime with comprehensive error handling
* Wine compatibility analysis and environment diagnostics
* Ada32 error code translation and reporting
* Progressive loading diagnostics with --verbose flag support

### Error Handling

* Detailed Windows error code translation
* Wine crash detection and reporting
* Ada32 error code interpretation with descriptive messages
* DLL loading diagnostics and dependency resolution

### FDO File Formats

**Source Format (.txt files):**
Human-readable structured text with commands like:
```
uni_start_stream <00x>
  man_start_object <independent, "Object Name">
    mat_object_id <32-105>
    mat_orientation <vcf>
    act_set_criterion <07x>
  man_end_object
uni_end_stream <>
```

**Binary Format (.str files):**
Official AOL binary format from .IDX database systems. Current test dataset contains 252 production .str files from AOL systems.

## License

[License details to be determined]

## Support

For build issues:
* Check Wine installation and MinGW cross-compiler setup
* Run diagnostics with --verbose flag
* Review golden test output for debugging
* Examine daemon logs for HTTP API issues

For runtime issues:
* Verify all DLL dependencies are present in build/bin/
* Check Wine environment with winecfg
* Test DLL loading with simple wine command

## Documentation

- **API_REFERENCE.md** - Complete HTTP API reference with error handling details
- **INTEGRATION_GUIDE.md** - Best practices and examples for client integration
- **samples/README_SAMPLES.md** - Guide to included sample FDO files
- **docs/** - Additional technical documentation