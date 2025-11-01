# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AtomForge v2.0 is a FastAPI-based web service for compiling and decompiling FDO (Field Data Object) files. The service manages long-lived Windows daemon processes (running under Wine in Docker) for low-latency operations.

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
2. **FDO Daemon Manager** (`api/src/fdo_daemon_manager.py`) - Single daemon lifecycle management
3. **FDO Daemon Pool Manager** (`api/src/fdo_daemon_pool_manager.py`) - Multi-daemon pool with health monitoring
4. **FDO Daemon Client** (`api/src/fdo_daemon_client.py`) - HTTP client for single daemon
5. **FDO Daemon Pool Client** (`api/src/fdo_daemon_pool_client.py`) - HTTP client with failover and load balancing
6. **FDO Tools Manager** (`api/src/fdo_tools_manager.py`) - Release discovery and validation

### Daemon Pool Architecture

The service supports two operation modes controlled by `FDO_DAEMON_POOL_ENABLED`:

**Single Daemon Mode** (FDO_DAEMON_POOL_ENABLED=false):
- One daemon instance on `FDO_DAEMON_PORT` (default: 8080)
- Simple, low memory footprint (~256MB)
- Single point of failure - daemon crash halts all operations
- Used by `FdoDaemonManager` and `FdoDaemonClient`

**Pool Mode** (FDO_DAEMON_POOL_ENABLED=true):
- Multiple daemon instances (default: 5) on consecutive ports (8080, 8081, 8082...)
- Round-robin load balancing across healthy daemons
- Automatic failover when daemons crash
- Circuit breaker pattern per daemon (opens after 3 failures)
- Background health monitoring (every 10s by default)
- Automatic restart with exponential backoff
- Higher memory requirement (~1GB for pool_size=5)
- Used by `FdoDaemonPoolManager` and `FdoDaemonPoolClient`

See `DAEMON_POOL_GUIDE.md` for detailed pool mode configuration.

### Binary Processing Pipeline

The service includes a complete pipeline for processing binary data:

1. **P3 Frame Parser** (`p3_frame_parser.py`) - Parses P3 protocol frames from binary data
2. **FDO Detector** (`fdo_detector.py`) - Detects FDO streams within parsed frames
3. **FDO Atom Parser** (`fdo_atom_parser.py`) - Parses FDO atom structure and action blocks
4. **FDO Chunker** (`fdo_chunker.py`) - Splits FDO scripts into P3 payload chunks (emulates AOLBUF.AOL)
5. **P3 Payload Builder** (`p3_payload_builder.py`) - Constructs P3 payloads with headers
6. **JSONL Processor** (`jsonl_processor.py`) - Processes detection results in JSONL format

### Data Management
- **Database** (`database.py`) - SQLite database for script/file persistence
- **File Manager** (`file_manager.py`) - CRUD operations for saved scripts and files

### Key Directories
- `api/src/` - Python source code
- `api/static/` - Web UI (index.html, pool.html, script.js, style.css)
- `releases/atomforge-backend/` - Vendor backend (daemon, DLLs, samples)
  - `bin/` - Windows executables (fdo_daemon.exe, fdo_compiler.exe, Ada32.dll, Ada.bin)
  - `samples/` - Example FDO files
- `compiled_output/` - Compilation output (mounted volume)
- `validation_results/` - Validation results (mounted volume)

## Environment Variables

### Core Configuration
- `FDO_RELEASES_DIR` - Path to releases directory (default: `/atomforge/releases`)
- `HOST` - API server bind address (default: `0.0.0.0`)
- `PORT` - API server port (default: `8000`)
- `LOGLEVEL` - Logging level (default: `INFO`)

### Mode Selection
- `FDO_DAEMON_POOL_ENABLED` - Enable pool mode (default: `false`)

### Single Daemon Mode (FDO_DAEMON_POOL_ENABLED=false)
- `FDO_DAEMON_BIND` - Daemon bind address (default: `127.0.0.1`)
- `FDO_DAEMON_PORT` - Daemon port (default: `8080`)

### Pool Mode (FDO_DAEMON_POOL_ENABLED=true)
- `FDO_DAEMON_POOL_SIZE` - Number of daemon instances (default: `5`, range: 1-MAX_SIZE)
- `FDO_DAEMON_POOL_MAX_SIZE` - Maximum allowed pool size (default: `100`, configurable upper limit)
- `FDO_DAEMON_POOL_BASE_PORT` - Starting port for pool (default: `8080`)
- `FDO_DAEMON_RESTART_DELAY` - Delay before restart in seconds (default: `2.0`)
- `FDO_DAEMON_HEALTH_INTERVAL` - Health check frequency in seconds (default: `10.0`)
- `FDO_DAEMON_MAX_RESTART_ATTEMPTS` - Max restart attempts (default: `5`)
- `FDO_DAEMON_MAX_RETRIES` - Request retry attempts (default: `3`)
- `FDO_DAEMON_REQUEST_TIMEOUT` - Timeout per request in seconds (default: `10.0`)
- `FDO_DAEMON_CIRCUIT_BREAKER_THRESHOLD` - Failures before opening circuit breaker (default: `3`)

### Wine Configuration
- `WINE` - Wine executable path (default: `wine`)
- `WINEPREFIX` - Wine prefix directory (default: `/wine`)
- `WINEARCH` - Wine architecture (default: `win32`)
- `WINEDEBUG` - Wine debug level (default: `-all`)

## API Endpoints

### Core Operations
- `POST /compile` - Compile FDO source to binary
- `POST /decompile` - Decompile binary to FDO source
- `GET /examples` - Get example FDO files
- `GET /health` - Service health (includes pool status if enabled)

### Pool Mode Endpoints (when FDO_DAEMON_POOL_ENABLED=true)
- `GET /health/pool` - Detailed pool health with per-daemon metrics
- `POST /pool/reset-circuit-breakers` - Reset all circuit breakers
- `GET /pool` - Pool dashboard UI (static HTML)

### File Management
- `POST /scripts` - Save FDO script
- `GET /scripts` - List saved scripts
- `GET /scripts/{id}` - Get specific script
- `PUT /scripts/{id}` - Update script
- `DELETE /scripts/{id}` - Delete script

### Binary Processing
- `POST /parse-p3-frames` - Parse P3 frames from binary data
- `POST /detect-fdo-in-binary` - Detect FDO streams in binary
- `POST /chunk-fdo` - Chunk FDO script into P3 payloads
- `POST /process-jsonl-detections` - Process JSONL detection results

### WebSocket
- `WS /ws` - WebSocket connection for real-time updates

## Implementation Notes

### Daemon Management
- Daemons run as Windows executables via Wine (32-bit)
- Requires Ada32.dll and Ada.bin in the same directory
- In pool mode, each daemon gets an isolated working directory with symlinked DLLs
- Health checks occur via GET `/health` on daemon port(s)
- Startup timeout is 12 seconds by default

### Release Discovery
- Releases must be in `releases/atomforge-backend/bin/` structure
- Required files: `fdo_daemon.exe`, `fdo_compiler.exe`, `fdo_decompiler.exe`, `Ada32.dll`, `Ada.bin`
- FdoToolsManager validates release structure on startup

### Error Handling
- Daemon errors return JSON with structured error information (code, line, context, hint)
- HTTP status codes: 400 (syntax error), 422 (semantic error), 500 (server error)
- Pool client implements retry logic with exponential backoff
- Circuit breakers prevent cascading failures in pool mode

### Web UI
- Main interface: `index.html` - Compile/decompile operations with hex/source views
- Pool dashboard: `pool.html` - Real-time pool health monitoring (auto-refresh every 5s)
- JavaScript: `script.js` - Client-side logic
- Styling: `style.css` - UI styling

## Common Tasks

### Adding a New API Endpoint
1. Add route handler in `api/src/api_server.py`
2. Define Pydantic models for request/response
3. Implement business logic or delegate to daemon client
4. Update OpenAPI docs with endpoint description

### Modifying Daemon Behavior
- For single daemon: edit `FdoDaemonManager` in `fdo_daemon_manager.py`
- For pool mode: edit `FdoDaemonPoolManager` in `fdo_daemon_pool_manager.py`
- Daemon protocol changes require updating both client and daemon executable

### Adding Binary Processing Features
- Create new module in `api/src/` (e.g., `fdo_new_feature.py`)
- Import in `api_server.py`
- Add endpoint to expose functionality

### Switching Between Daemon Modes
```bash
# Enable pool mode
# Edit docker-compose.yml:
- FDO_DAEMON_POOL_ENABLED=true
- FDO_DAEMON_POOL_SIZE=5
# Increase memory limit to 1G in deploy.resources.limits

# Disable pool mode (revert to single daemon)
- FDO_DAEMON_POOL_ENABLED=false
# Can reduce memory limit back to 256M
```

### Debugging Daemon Issues
```bash
# Check daemon process(es)
docker exec atomforge-v2 ps aux | grep fdo_daemon

# View Wine output (not redirected in current setup)
docker logs atomforge-v2 | grep wine

# Manual single daemon start for testing
docker exec -it atomforge-v2 wine releases/atomforge-backend/bin/fdo_daemon.exe --port 8080

# Pool mode: check health of all daemons
curl http://localhost:8000/health/pool | jq

# Pool mode: monitor in real-time
watch -n 5 'curl -s http://localhost:8000/health/pool | jq .instances_by_state'

# Pool mode: reset circuit breakers
curl -X POST http://localhost:8000/pool/reset-circuit-breakers

# View pool dashboard
open http://localhost:8000/pool
```

## Resource Constraints

### Single Daemon Mode
- Memory limit: 256MB
- CPU limit: 0.5 cores

### Pool Mode (pool_size=5)
- Memory limit: 1GB (recommended)
- CPU limit: 1.0 cores (recommended)
- Adjust in `docker-compose.yml` under `deploy.resources` if needed
- See `DAEMON_POOL_GUIDE.md` for scaling guidance
