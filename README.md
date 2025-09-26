# AtomForge v2.0

**FDO Compiler & Decompiler with Python Module Integration**

AtomForge v2.0 provides a modern web interface for compiling and decompiling FDO files using the new FDO Daemon (HTTP) running under Wine inside the container.

```
 _____ _____ _____ _____ _____ _____ _____ _____ _____
|  _  |_   _|     |     |   __|     |  _  |   __|   __|
|     | | | |  |  | | | |   __|  |  |     |  |  |   __|
|__|__| |_| |_____|_|_|_|__|__|_____|__|__|_____|_____|
```

## ✨ What's New in v2.0

- **🚀 Low-latency Daemon** - HTTP daemon-first integration for speed and stability
- **🔧 Simplified Architecture** - Single container manages the daemon lifecycle internally
- **📦 Release-Based Deployment** - Automatic discovery of vendor backend drop
- **🐳 Streamlined Docker** - Single container, Wine executes Windows binaries

## Features

- **High-performance FDO compilation** via in-container HTTP daemon
- **Compile FDO source code to binary**
- **Decompile FDO binaries back to source**
- **Web interface** with file upload support
- **Hex input/output** for binary data
- **Release management** - Automatic FDO Tools version discovery
- **Docker containerized** with Wine environment

## Quick Start

### Docker (Recommended)

```bash
# Build and run AtomForge v2.0
docker build -t atomforge-v2 .
docker run -d -p 8000:8000 --name atomforge atomforge-v2
```

Access at: **http://localhost:8000**

### Docker Compose

```bash
docker compose up --build
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Architecture

### FDO Tools Integration

AtomForge v2.0 uses the **FDO Daemon HTTP API** for all compilation operations:

```python
# High-performance compilation via HTTP daemon
# POST /compile (text/plain) -> application/octet-stream
# POST /decompile (application/octet-stream) -> text/plain
```

### Release Management

The system automatically discovers the vendor backend drop:

```
releases/
└── atomforge-backend/
    ├── fdo_daemon.exe
    ├── fdo_compiler.exe
    ├── fdo_decompiler.exe
    ├── Ada32.dll
    ├── Ada.bin
    ├── mfc42.dll
    └── docs/README-BINARY.md
```

### Project Structure

```
AtomForge/
├── api/
│   ├── src/
│   │   ├── api_server.py           # FastAPI server (daemon-first)
│   │   ├── fdo_tools_manager.py    # Release discovery & management
│   │   ├── fdo_daemon_client.py    # HTTP client for daemon
│   │   └── fdo_daemon_manager.py   # Process lifecycle for daemon (Wine)
│   ├── static/                     # Web interface files
│   └── requirements.txt
├── releases/                       # FDO Tools releases directory
│   └── atomforge-backend/          # Current vendor backend drop
├── bin/                           # Legacy directory (golden tests only)
│   └── fdo_compiler_decompiler/
│       └── golden_tests_immutable/ # Test files for validation
├── Dockerfile                     # Container definition
└── docker-compose.yml
```

## Usage

### Web Interface

1. **Navigate to http://localhost:8000**
2. **Choose Compile or Decompile mode** (tabs at the top)
3. **For Compile**: paste FDO source in the editor, then Run
4. **For Decompile**: choose File or Hex input
   - **File**: click drop area and select a file
   - **Hex**: paste raw hex (with or without spaces)
5. **Results appear** in output tabs (Status, Hex, Source)

**Shortcuts**:
- `Ctrl+Enter` (Windows/Linux) or `Cmd+Enter` (macOS) to Run
- Copy Hex for contiguous raw hex output
- Download buttons save binary or source to disk

### API Endpoints

#### Compile FDO Source
```bash
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{
    "source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n    mat_object_id <test-001>\n  man_end_object <>\nuni_end_stream <>",
    "normalize": true
  }'
```

#### Decompile FDO Binary
```bash
curl -X POST http://localhost:8000/decompile \
  -H "Content-Type: application/json" \
  -d '{
    "binary_data": "BASE64_ENCODED_BINARY_DATA",
    "format": "text"
  }'
```

> Note: The previous `/compile-split` and P3 extractor endpoints were removed.

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Get Examples
```bash
curl http://localhost:8000/examples
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health and daemon status |
| `/compile` | POST | Compile source to binary |
| `/decompile` | POST | Decompile binary to source |
| `/examples` | GET | Get available FDO examples |

## Environment

The Docker container includes:
- **Python 3.11** slim base
- **Wine32** for Windows executable support (daemon under Wine)
- **FDO Daemon** with automatic discovery
- **Ada32.dll, Ada.bin, mfc42.dll** - All required dependencies
- **Minimal runtime** - No supervisord or complex daemon management

## Performance

AtomForge v2.0 delivers significant performance improvements:

- **🚀 7x faster compilation** (400ms vs 2.9s average)
- **📡 Daemon-stdio communication** for minimal overhead
- **⚡ Direct Python integration** eliminates process startup costs
- **🎯 Immediate ROI** - Performance benefits from the first compilation

## Development

### Revving the AtomForge Backend (daemon)

1. **Replace the backend drop** under `releases/`:
   - Put the new vendor drop at `releases/atomforge-backend/` (contains `fdo_daemon.exe`, `fdo_compiler.exe`, DLLs, and `docs/README-BINARY.md`).
   - Keep all DLLs and `Ada.bin` next to the executables in the same folder.

2. **Rebuild and restart** (either path):
   ```bash
   # Docker
   docker compose up --build -d

   # Or if running locally, restart the FastAPI app
   ```

On startup, AtomForge discovers `releases/atomforge-backend/` and selects it automatically. No version flag is required.

### Testing

Run the comprehensive test suite:
```bash
python3 test_fdo_tools.py          # FDO Tools integration tests
./validate_api_v2.sh               # API endpoint validation
python3 test_golden_masters.py     # Golden master compilation tests
```

## Migration from v1.x

AtomForge v2.0 is a complete architectural rewrite:

- ✅ **Added**: Daemon-first HTTP integration
- 🔄 **Changed**: `bin/` → `releases/atomforge-backend` structure, simplified Docker setup

For migration details, see `MIGRATION.md`.

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs atomforge

# Verify Wine and dependencies
docker exec atomforge wine --version
```

### API Errors
```bash
# Check health status
curl http://localhost:8000/health

# Verify FDO Tools status
docker exec atomforge ls -la /atomforge/releases/
```

### Compilation Failures
```bash
# Check daemon health
curl -s http://localhost:8000/health | jq .

# Verify backend files are present
docker exec atomforge ls -la /atomforge/releases/atomforge-backend/

# Start of daemon is handled by the API process (under Wine). If needed, test the daemon manually:
docker exec atomforge wine /atomforge/releases/atomforge-backend/fdo_daemon.exe --port 8080
```

### Performance Issues
```bash
# Run performance validation
python3 test_golden_masters.py --performance

# Check daemon mode
curl -s http://localhost:8000/health | jq '.execution_mode'
```

## License

MIT License - See LICENSE file for details.

## Notes

This tool is intended for legitimate reverse engineering and analysis purposes.
The original Ada32.dll and executables are required for operation.