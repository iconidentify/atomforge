# AtomForge

FDO Compiler & Decompiler with Web Interface

AtomForge provides a web interface for compiling and decompiling FDO files using the original Ada32.dll.
Runs in Docker with Wine for cross-platform compatibility.

```
 _____ _____ _____ _____ _____ _____ _____ _____ _____
|  _  |_   _|     |     |   __|     |  _  |   __|   __|
|     | | | |  |  | | | |   __|  |  |     |  |  |   __|
|__|__| |_| |_____|_|_|_|__|__|_____|__|__|_____|_____|
```

## Features

- Compile FDO source code to binary
- Decompile FDO binaries back to source
- Web interface with file upload support
- Hex input/output for binary data
- Native Ada32.dll execution via Wine
- Docker containerized environment

## Quick Start

### Docker (Recommended)

```bash
docker build -t atomforge-full .
docker run -p 8000:8000 atomforge-full
```

Access at: http://localhost:8000

### Manual Setup

Requirements:
- Python 3.11+
- Wine (for Ada32.dll execution)

```bash
# Install dependencies
pip install -r api/requirements.txt

# Run server
cd api && python src/api_server.py
```

## Usage

### Web Interface

1. Choose Compile or Decompile mode
2. Upload files or paste text/hex data
3. Click the action button
4. Download results or copy output

### API

Compile FDO source:
```bash
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n    mat_object_id <test-001>\n  man_end_object <>\nuni_end_stream <>"}'
```

Decompile FDO binary:
```bash
curl -X POST http://localhost:8000/decompile \
  -H "Content-Type: application/json" \
  -d '{"binary_data": "BASE64_ENCODED_BINARY_DATA"}'
```

## Project Structure

```
AtomForge/
├── api/
│   ├── src/
│   │   ├── api_server.py       # FastAPI web server
│   │   ├── fdo_compiler.py     # Compilation logic
│   │   └── fdo_decompiler.py   # Decompilation logic
│   └── static/                 # Web interface files
├── bin/
│   └── fdo_compiler_decompiler/
│       ├── fdo_compiler.exe    # Windows compiler
│       ├── fdo_decompiler.exe  # Windows decompiler
│       ├── Ada32.dll           # Runtime library
│       └── Ada.bin             # Additional dependencies
└── Dockerfile                  # Container definition
```

## File Format Support

### Input
- Text files (.txt, .fdo) for compilation
- Binary files (.fdo, .str, .bin) for decompilation
- Hex strings (with or without spaces)

### Output
- Binary FDO files from compilation
- Text source code from decompilation
- Hex preview for inspection

## API Endpoints

- `POST /compile` - Compile source to binary
- `POST /decompile` - Decompile binary to source
- `GET /examples` - Get example FDO files
- `GET /health` - Service health check

## Environment

The Docker container includes:
- Python 3.11 slim base
- Wine32 for Windows executable support
- Ada32.dll registered and ready
- Minimal runtime dependencies

## License

MIT License - See LICENSE file for details.

## Notes

This tool is intended for legitimate reverse engineering and analysis purposes.
The original Ada32.dll and executables are required for operation.