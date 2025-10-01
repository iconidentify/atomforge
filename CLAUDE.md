# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AtomForge v2.0 is a FastAPI-based web service for compiling and decompiling FDO (Field Data Object) files. The service manages a long-lived Windows daemon process (running under Wine in Docker) for low-latency operations.

## Development Commands

### Docker (Recommended)
```bash
# Build and run
docker compose up --build

# Rebuild without cache
docker compose build --no-cache

# View logs
docker logs -f atomforge-v2

# Stop service
docker compose down
```

### Local Development
```bash
# Install dependencies
cd api
pip install -r requirements.txt

# Run API server directly
python3 -m api.src.api_server
```

### Testing
```bash
# Health check
curl http://localhost:8000/health

# Get examples
curl http://localhost:8000/examples

# Compile FDO source
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n    mat_object_id <test-001>\n  man_end_object <>\nuni_end_stream <>", "normalize": true}'

# Decompile binary
curl -X POST http://localhost:8000/decompile \
  -H "Content-Type: application/json" \
  -d '{"binary_data": "BASE64_DATA", "format": "text"}'
```

## Architecture

### Service Layers
1. **FastAPI Server** (`api/src/api_server.py`) - HTTP endpoints, request/response handling
2. **FDO Daemon Manager** (`api/src/fdo_daemon_manager.py`) - Wine daemon lifecycle management
3. **FDO Daemon Client** (`api/src/fdo_daemon_client.py`) - HTTP client for daemon communication
4. **FDO Tools Manager** (`api/src/fdo_tools_manager.py`) - Release discovery and validation

### Daemon Pool Architecture (Optional)
The service supports two operation modes:
- **Single Daemon Mode**: One daemon instance (default in docker-compose.yml)
- **Pool Mode**: Multiple daemon instances for resiliency and load balancing

Set `FDO_DAEMON_POOL_ENABLED=true` to enable pool mode (see DAEMON_POOL_GUIDE.md for details).

### Binary Processing Modules
- **FDO Atom Parser** (`fdo_atom_parser.py`) - Parses FDO atom structure
- **FDO Chunker** (`fdo_chunker.py`) - Splits binary data into chunks
- **FDO Detector** (`fdo_detector.py`) - Detects FDO streams in binary data
- **P3 Frame Parser** (`p3_frame_parser.py`) - Parses P3 protocol frames
- **P3 Payload Builder** (`p3_payload_builder.py`) - Constructs P3 payloads
- **JSONL Processor** (`jsonl_processor.py`) - Processes JSONL detection results

### Data Management
- **Database** (`database.py`) - SQLite database for script/file persistence
- **File Manager** (`file_manager.py`) - Script and file CRUD operations

### Key Directories
- `api/src/` - Python source code
- `api/static/` - Web UI (HTML/CSS/JS)
- `releases/atomforge-backend/` - Vendor backend (daemon, DLLs, samples)
  - `bin/` - Windows executables (fdo_daemon.exe, fdo_compiler.exe, Ada32.dll)
  - `samples/` - Example FDO files
- `compiled_output/` - Compilation output (mounted volume)
- `validation_results/` - Validation results (mounted volume)

## Environment Variables

### Core Configuration
- `FDO_RELEASES_DIR` - Path to releases directory (default: `/atomforge/releases`)
- `HOST` - API server bind address (default: `0.0.0.0`)
- `PORT` - API server port (default: `8000`)
- `LOGLEVEL` - Logging level (default: `INFO`)

### Single Daemon Mode (FDO_DAEMON_POOL_ENABLED=false)
- `FDO_DAEMON_BIND` - Daemon bind address (default: `127.0.0.1`)
- `FDO_DAEMON_PORT` - Daemon port (default: `8080`)

### Pool Mode (FDO_DAEMON_POOL_ENABLED=true)
- `FDO_DAEMON_POOL_SIZE` - Number of daemon instances (default: `5`)
- `FDO_DAEMON_POOL_BASE_PORT` - Starting port for pool (default: `8080`)
- `FDO_DAEMON_RESTART_DELAY` - Delay before restart (default: `2.0`)
- `FDO_DAEMON_HEALTH_INTERVAL` - Health check frequency (default: `10.0`)
- `FDO_DAEMON_MAX_RESTART_ATTEMPTS` - Max restart attempts (default: `5`)

### Wine Configuration
- `WINE` - Wine executable path (default: `wine`)
- `WINEPREFIX` - Wine prefix directory (default: `/wine`)
- `WINEARCH` - Wine architecture (default: `win32`)
- `WINEDEBUG` - Wine debug level (default: `-all`)

## Implementation Notes

### Daemon Management
- The daemon runs as a Windows executable via Wine
- Requires Ada32.dll and Ada.bin in the same directory as the daemon
- Health checks occur via GET `/health` on daemon port
- Startup timeout is 12 seconds by default

### Release Discovery
- Releases must be in `releases/atomforge-backend/bin/` structure
- Required files: `fdo_daemon.exe`, `fdo_compiler.exe`, `fdo_decompiler.exe`, `Ada32.dll`, `Ada.bin`
- FdoToolsManager validates release structure on startup

### Error Handling
- Daemon errors return JSON with structured error information (code, line, context, hint)
- HTTP status codes: 400 (syntax error), 422 (semantic error), 500 (server error)
- Client implements retry logic with exponential backoff

### Web UI
- Single-page application in `api/static/`
- Supports compile/decompile operations with hex/source views
- Real-time compilation status and error display
- Example files loaded from `/examples` endpoint

## Common Tasks

### Adding a New API Endpoint
1. Add route handler in `api/src/api_server.py`
2. Define Pydantic models for request/response
3. Implement business logic or delegate to daemon client
4. Update OpenAPI docs with endpoint description

### Modifying Daemon Behavior
- For single daemon: edit `FdoDaemonManager` in `fdo_daemon_manager.py`
- For pool mode: edit `FdoDaemonPoolManager` (not in current files)
- Daemon protocol changes require updating both client and daemon executable

### Adding Binary Processing Features
- Create new module in `api/src/` (e.g., `fdo_new_feature.py`)
- Import in `api_server.py`
- Add endpoint to expose functionality

### Debugging Daemon Issues
```bash
# Check daemon process
docker exec atomforge-v2 ps aux | grep fdo_daemon

# View Wine output (not redirected in current setup)
docker logs atomforge-v2 | grep wine

# Manual daemon start for testing
docker exec -it atomforge-v2 wine releases/atomforge-backend/bin/fdo_daemon.exe --port 8080
```

## Resource Constraints

Production deployment uses:
- Memory limit: 256MB
- CPU limit: 0.5 cores
- Adjust in `docker-compose.yml` under `deploy.resources` if needed
