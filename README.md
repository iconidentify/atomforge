# ADA32 FDO Compiler

A clean, focused toolkit for compiling AOL atom stream text files (.txt) to binary stream files (.str) using the original Ada32.dll library in a Wine-based Docker environment.

## Overview

This repository contains the essential functionality for FDO (Flap Data Object) compilation using AOL's original Ada32.dll. The tool takes raw FDO text input and produces binary atom stream output through the authentic Ada32.dll compilation pipeline.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Usage

1. **Start the compilation environment:**
   ```bash
   docker-compose run --rm ada32-wine bash
   ```

2. **Compile FDO to binary:**
   ```bash
   cd /ada32_fdo_compiler
   wine bin/ada32_compiler.exe
   ```

## Architecture

### Core Components
- **Ada32.dll** (239KB) - Original AOL compilation library
- **ada32_compiler.exe** - Working C compilation tool
- **Wine x86 Emulation** - Cross-platform Windows compatibility
- **Docker Containerized** - Isolated, reproducible environment

### Directory Structure
```
ada32_fdo_compiler/
├── src/production/          # Core C source code
│   ├── ada32_compiler.c     # Main compiler implementation
│   ├── ada32_production_test.c # Production test code
│   ├── simple_compiler.c    # Simplified compiler interface
│   └── fdo_compiler.c       # Alternative compiler
├── src/analysis/            # Analysis and debugging tools
│   ├── ada32_debugger.c     # Debugging utilities
│   ├── ada32_diagnostic.c   # Diagnostic tools
│   └── analyze_format_differences.c # Format analysis
├── bin/                     # Executables and libraries
│   ├── ada32_compiler.exe   # Working executable
│   └── dlls/                # Required DLLs
│       ├── Ada32.dll        # Core compilation library
│       ├── Dbaol32.dll      # Database functions
│       └── Supersub.dll     # Support library
├── golden_tests_immutable/  # Reference data (DO NOT MODIFY)
├── research_materials/      # Original AOL tools (reference only)
├── test_fixtures/           # Sample input files
└── docker-compose.yml       # Build environment
```

## Key Features

- **Authentic Compilation** - Uses original Ada32.dll from AOL
- **Working Executable** - ada32_compiler.exe successfully compiles FDO
- **Wine Integration** - Cross-platform Windows emulation
- **Reference Data** - Comprehensive golden test suite
- **Clean Architecture** - Focused on core functionality

## File Formats

### Input: FDO Text (.txt)
```
uni_start_stream <00x>
  man_start_object <independent, "Test Room">
  ...
```

### Output: Binary Stream (.str)
Compiled binary format from Ada32.dll (typically 413 bytes)

## Development

### Core Working Components
- **ada32_compiler.c** - Main production compiler (working)
- **ada32_production_test.c** - Production test implementation (working)
- **Ada32.dll** - Original AOL library (239KB, 1997)
- **Wine/Docker** - Cross-platform execution environment

### Research Status
This represents the working FDO compilation pipeline using authentic Ada32.dll. The core functionality successfully converts FDO text to binary streams.

## Testing

Use the test fixtures in `test_fixtures/` or the comprehensive reference data in `golden_tests_immutable/` to validate compilation.

## Research Materials

The `research_materials/` directory contains original AOL tools for reference:
- **STAR Tool** - Alternative Ada32.dll implementation
- **DBViewer** - Original database viewer application
- **Ada32_exports.json** - Function export definitions

These are preserved for research purposes but are not required for core compilation functionality.
