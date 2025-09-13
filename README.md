# ADA32 FDO Compiler

A clean, focused toolkit for compiling atom stream text files (.txt) to binary stream files (.str) using the Ada32.dll library. Available as both a command-line tool and HTTP REST API.

## Overview

This repository contains the essential functionality for FDO (Flap Data Object) compilation using the Ada32.dll library. The tool takes raw FDO text input and produces binary atom stream output through the Ada32.dll compilation pipeline.

**Features:**
- 🔧 **Command Line Interface** - Simple Python harness for local compilation
- 🌐 **HTTP REST API** - Containerized web service for remote compilation
- 🐳 **Docker Ready** - Wine environment with Ada32.dll pre-configured
- 📁 **Shared Architecture** - Reusable compiler module for both CLI and API
- ⚡ **Binary Preservation** - Maintains authentic FDO binary format

## Quick Start

### Option A: Docker Release (Easiest)

```bash
# Download and run the latest release
docker run -p 8000:8000 ghcr.io/iconidentify/ada32-toolkit:latest

# Open API documentation
open http://localhost:8000

# Compile FDO (example)
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n  man_end_object <>\nman_end_stream <>"}' \
  --output test.fdo
```

### Option B: Development Setup

#### Prerequisites
- Docker and Docker Compose
- Git
- Python 3.6+

### Usage

#### Option 1: Command Line Interface
```bash
# Compile FDO text to binary
python fdo_compile.py input.txt [output.fdo]
```

This automatically:
- ✅ Builds/starts Docker container
- ✅ Escapes special characters (& → 26x)  
- ✅ Runs compilation with Ada32.dll
- ✅ Returns compiled .fdo file

#### Option 2: HTTP REST API
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

#### Option 3: Manual Docker Usage
```bash
# Build and run container
cd build_tools
docker-compose run --rm ada32-wine bash

# Inside container, compile manually
cd /ada32_toolkit
wine bin/ada32_compiler.exe input.txt output.str
```

## Architecture

### Core Components
- **Ada32.dll** (239KB) - FDO compilation library
- **ada32_compiler.exe** - Working C compilation tool
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
ada32_fdo_compiler/
├── api/                     # HTTP REST API service
│   ├── src/                 # API source code
│   │   ├── api_server.py    # FastAPI HTTP service
│   │   └── fdo_compiler.py  # Shared compiler module
│   ├── Dockerfile           # API container definition
│   ├── docker-compose.yml   # API service configuration
│   └── README.md            # API documentation
├── src/                     # Core C source code
│   └── ada32_compiler.c     # ✅ MAIN PRODUCTION COMPILER (Ada32.dll + Wine)
├── bin/                     # Executables and libraries
│   ├── ada32_compiler.exe   # Working executable
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

## Docker Releases

Pre-built Docker images are available for easy deployment:

### Latest Release
```bash
docker run -p 8000:8000 ghcr.io/iconidentify/ada32-toolkit:latest
```

### Specific Version
```bash
# List available versions
curl -s https://api.github.com/repos/iconidentify/ada32-toolkit/releases | grep "tag_name"

# Run specific version
docker run -p 8000:8000 ghcr.io/iconidentify/ada32-toolkit:v1.0.0
```

### Docker Compose (Recommended)
```bash
# Download the API compose file
curl -O https://raw.githubusercontent.com/iconidentify/ada32-toolkit/main/docker-compose.api.yml

# Start the service
docker-compose -f docker-compose.api.yml up -d

# Check it's running
curl http://localhost:8000/health
```

### Koyeb Cloud (Free & Simple)
```bash
# 1. Sign up at https://app.koyeb.com/
# 2. Connect your GitHub repo
# 3. Deploy with these settings:
#    - Branch: master
#    - Work Directory: api
#    - Dockerfile: api/Dockerfile.koyeb
#    - Port: 8000
#    - Instance: Free (512MB)

# Your API will be live instantly!
# Example: https://fdo-api-yourname.koyeb.app
```

### Image Details
- **Registry**: `ghcr.io/iconidentify/ada32-toolkit`
- **Size**: ~500MB (includes Wine + Ada32.dll)
- **Platforms**: linux/amd64
- **Auto-updated**: Latest tag tracks master branch

## Research Materials

The `research_materials/` directory contains original reference tools:
- **STAR Tool** - Alternative Ada32.dll implementation
- **DBViewer** - Original database viewer application (full installation)
- **Ada32_exports.json** - Function export definitions
- **Essential files** - Ada.bin, GIDINFO.INF, and other dependencies (copied to bin/dlls/)

These are preserved for research purposes but are not required for core compilation functionality.
