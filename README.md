```
+--------------------------------------------------------------+
|                          ATOMFORGE v2.0                      |
|     FDO Compiler / Decompiler (FastAPI + Daemon + Docker)    |
+--------------------------------------------------------------+
```

## Overview
AtomForge v2.0 provides a modern web and HTTP interface for compiling and decompiling FDO (Field Data Object) files. The FastAPI server manages a long-lived vendor daemon (running under Wine) for low-latency operations.

## What's New in v2.0
- Daemon-first HTTP integration (no per-request process spawn)
- Single-container design; daemon lifecycle managed by the API
- Automatic discovery of the vendor backend drop under `releases/`
- Streamlined Docker image; Wine executes the Windows binaries

## Quick Start
### Docker (recommended)
```bash
docker build -t atomforge-v2 .
docker run -d -p 8000:8000 --name atomforge atomforge-v2
```
Open: `http://localhost:8000`

### Docker Compose
```bash
docker compose up --build
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Usage
### Web Interface
1. Go to `http://localhost:8000`
2. Choose Compile or Decompile mode
3. Compile: paste FDO source and run
4. Decompile: choose File or Hex input and run
5. Results appear in tabs (Status, Hex, Source)

### API Examples
Compile FDO Source:
```bash
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{
        "source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n    mat_object_id <test-001>\n  man_end_object <>\nuni_end_stream <>",
        "normalize": true
      }'
```

Decompile FDO Binary:
```bash
curl -X POST http://localhost:8000/decompile \
  -H "Content-Type: application/json" \
  -d '{
        "binary_data": "BASE64_ENCODED_BINARY_DATA",
        "format": "text"
      }'
```

Health:
```bash
curl http://localhost:8000/health
```

Examples:
```bash
curl http://localhost:8000/examples
```

## Architecture
```
AtomForge/
├── api/
│   ├── src/
│   │   ├── api_server.py         # FastAPI server (daemon-first)
│   │   ├── fdo_tools_manager.py  # Release discovery & management
│   │   ├── fdo_daemon_client.py  # HTTP client for daemon
│   │   └── fdo_daemon_manager.py # Daemon lifecycle (Wine)
│   ├── static/                   # Web interface files
│   └── requirements.txt
├── releases/
│   └── atomforge-backend/        # Vendor backend drop (daemon, DLLs, samples)
├── Dockerfile
└── docker-compose.yml
```

Daemon protocol (conceptual):
```
POST /compile    text/plain             -> application/octet-stream
POST /decompile  application/octet-stream -> text/plain
```

## License
MIT License. See `LICENSE` for details.

## Notes
Use AtomForge for legitimate reverse engineering and analysis only. Vendor
components (e.g., Ada32.dll) are required for operation and are not included
here.
