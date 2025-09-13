# AtomForge

**AtomForge** - A powerful toolkit for forging atom streams, transforming text-based FDO definitions into optimized binary formats using the Ada32.dll compilation engine. Available as both a command-line forge and HTTP REST API.

## Overview

**AtomForge** is a precision toolkit for crafting perfect atom streams. Like a master blacksmith forging metal into intricate shapes, AtomForge transforms raw FDO text definitions into highly optimized binary formats using the powerful Ada32.dll compilation engine.

**Forge Features:**
- 🔨 **Command Line Forge** - Powerful Python harness for precision compilation
- 🌐 **HTTP REST API** - Containerized web service for remote atom crafting
- 🐳 **Docker Forged** - Wine environment with Ada32.dll perfectly tempered
- 📁 **Shared Architecture** - Reusable compiler module across all interfaces
- ⚡ **Binary Mastery** - Preserves authentic FDO binary craftsmanship

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git
- Python 3.6+

### Usage

#### Command Line Interface
```bash
# Compile FDO text to binary
python fdo_compile.py input.txt [output.fdo]
```

This automatically:
- ✅ Builds/starts Docker container
- ✅ Escapes special characters (& → 26x)  
- ✅ Runs compilation with Ada32.dll
- ✅ Returns compiled .fdo file

#### HTTP REST API
```bash
# Start the API service
cd api
docker-compose up --build

# API available at http://localhost:8000
```

**Compile via API:**
```bash
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n  man_end_object <>\nuni_end_stream <>"}' \
  --output compiled.fdo

# Check health
curl http://localhost:8000/health
```

**API Features:**
- 🌐 Clean REST endpoints at `/compile` and `/health`
- 📄 Swagger UI documentation at http://localhost:8000/
- 🔄 Binary response for successful compilation
- 📝 Detailed JSON error responses for failures
- ⚡ Fast Wine-based execution inside container

#### Manual Docker Usage
```bash
# Build and run container
cd build_tools
docker-compose run --rm ada32-wine bash

# Inside container, compile manually
cd /ada32_toolkit
wine bin/atomforge.exe input.txt output.str
```

## Architecture

### Core Components
- **Ada32.dll** (239KB) - FDO compilation library
- **atomforge.exe** - Working C compilation tool
- **fdo_compile.py** - Python harness for automated compilation
- **Wine x86 Emulation** - Cross-platform Windows compatibility
- **Docker Containerized** - Isolated, reproducible environment

### Python Harness Features
The `fdo_compile.py` script provides:
- **Automatic Docker Management** - Builds and runs containers transparently
- **Character Escaping** - Converts `&` to `26x` (required by Ada32.dll)
- **Cross-Platform** - Works on Mac ARM, Linux, Windows
- **Simple Interface** - Single command compilation
- **Error Handling** - Clear error messages and cleanup

### Directory Structure
```
atomforge/
├── api/                     # HTTP REST API service
│   ├── src/                 # API source code
│   │   ├── api_server.py    # FastAPI HTTP service
│   │   └── fdo_compiler.py  # Shared compiler module
│   ├── Dockerfile           # API container definition
│   ├── docker-compose.yml   # API service configuration
│   └── README.md            # API documentation
├── src/                     # Core C source code
│   └── atomforge.c          # ✅ MAIN PRODUCTION COMPILER (Ada32.dll + Wine)
├── bin/                     # Executables and libraries
│   ├── atomforge.exe        # Working executable
│   └── dlls/                # Essential Ada32.dll dependencies
│       ├── Ada32.dll        # Core compilation library (239KB)
│       ├── Ada.bin          # Token definition file (121KB)
│       └── GIDINFO.INF      # Configuration file (25 bytes)
├── golden_tests_immutable/  # Reference data + sample inputs (DO NOT MODIFY)
├── research_materials/      # Original reference tools
├── fdo_compile.py           # Python harness for automated compilation
└── build_tools/             # Docker build configuration
    ├── docker-compose.yml   # Container orchestration
    └── Dockerfile           # Container definition
```

## Key Features

- **Authentic Compilation** - Uses Ada32.dll for FDO processing
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
- **fdo_compile.py** - Command-line Python harness 
- **api_server.py** - HTTP REST API service
- **fdo_compiler.py** - Shared compiler module (reusable)
- **Ada32.dll** - FDO compilation library (239KB)
- **Wine/Docker** - Cross-platform execution environment

### Research Status
This represents the working FDO compilation pipeline using authentic Ada32.dll. The core functionality successfully converts FDO text to binary streams.

## Testing

Use the comprehensive reference data in `golden_tests_immutable/` to validate compilation.

## Research Materials

The `research_materials/` directory contains original reference tools:
- **STAR Tool** - Alternative Ada32.dll implementation
- **DBViewer** - Original database viewer application (full installation)
- **Ada32_exports.json** - Function export definitions
- **Essential files** - Ada.bin, GIDINFO.INF, and other dependencies (copied to bin/dlls/)

These are preserved for research purposes but are not required for core compilation functionality.
