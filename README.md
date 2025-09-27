===============================================================================
                              A T O M F O R G E   v2.0
===============================================================================
                  F D O   C O M P I L E R  +  D E C O M P I L E R
                     ( FastAPI + Daemon + Docker + Wine32 )
-------------------------------------------------------------------------------
README.TXT   |   Last Updated: 2025-09-27   |   License: MIT
-------------------------------------------------------------------------------

                         _______  _______  _______  _______
                        |   _   ||   _   ||       ||       |
                        |.  1___||.  |   ||.|   | ||.|   | |
                        |.  __)  |.  |   ||.|   | ||.|   | |
                        |:  |    |:  1   ||:  1   ||:  1   |
                        |::.|    |::.. . ||::.. . ||::.. . |
                        `---'    `-------'`-------'`-------'

-------------------------------------------------------------------------------
TABLE OF CONTENTS
-------------------------------------------------------------------------------
  [01] INTRODUCTION
  [02] WHAT'S NEW IN v2.0
  [03] FEATURES
  [04] QUICK START
  [05] ARCHITECTURE
  [06] USAGE (WEB + API)
  [07] API REFERENCE (ENDPOINTS)
  [08] ENVIRONMENT
  [09] PERFORMANCE NOTES
  [10] DEVELOPMENT / BACKEND DROP
  [11] TESTING
  [12] MIGRATION FROM v1.x
  [13] TROUBLESHOOTING
  [14] LICENSE
  [15] NOTES

-------------------------------------------------------------------------------
[01] INTRODUCTION
-------------------------------------------------------------------------------
AtomForge v2.0 delivers a daemon-first workflow for compiling and decompiling
FDO (Field Data Object) artifacts. A FastAPI service speaks to the vendor
FDO Daemon (running under Wine) for low-latency compile/decompile operations.

This document is intentionally formatted in nostalgic, over-the-top 90s ASCII.

-------------------------------------------------------------------------------
[02] WHAT'S NEW IN v2.0
-------------------------------------------------------------------------------
- Low-latency HTTP daemon integration (no per-request process spawn)
- Simplified single-container design; daemon lifecycle managed in-process
- Release discovery from the bundled vendor backend directory
- Lean Docker image; Wine executes Windows binaries inside the container

-------------------------------------------------------------------------------
[03] FEATURES
-------------------------------------------------------------------------------
- High-performance FDO compilation via HTTP daemon
- Compile source -> binary; Decompile binary -> source
- Clean web UI with file upload and hex input modes
- Hex output view for raw binary data
- Automatic discovery of vendor drop under `releases/`
- Fully containerized with Wine32

-------------------------------------------------------------------------------
[04] QUICK START
-------------------------------------------------------------------------------
( A ) Docker (Recommended )

    $ docker build -t atomforge-v2 .
    $ docker run -d -p 8000:8000 --name atomforge atomforge-v2

    > Open: http://localhost:8000

( B ) Docker Compose

    $ docker compose up --build

( C ) Health Check

    $ curl http://localhost:8000/health

-------------------------------------------------------------------------------
[05] ARCHITECTURE
-------------------------------------------------------------------------------
FDO Tools are accessed via a long-lived HTTP daemon (under Wine). The API
process starts and manages the daemon, then communicates over HTTP for both
compile and decompile requests.

Directory Highlights:

    AtomForge/
      api/
        src/
          api_server.py         FastAPI server (daemon-first)
          fdo_tools_manager.py  Release discovery & selection
          fdo_daemon_client.py  HTTP client for daemon
          fdo_daemon_manager.py Daemon lifecycle (Wine)
        static/                 Web assets (HTML/CSS/JS)
        requirements.txt        Runtime deps
      releases/
        atomforge-backend/      Vendor backend drop (daemon, DLLs, samples)
      Dockerfile                Container definition
      docker-compose.yml        Compose definition

Daemon Protocol (conceptual):

    POST /compile   text/plain            -> application/octet-stream
    POST /decompile application/octet-stream -> text/plain

-------------------------------------------------------------------------------
[06] USAGE (WEB + API)
-------------------------------------------------------------------------------
WEB INTERFACE
  1) Navigate to: http://localhost:8000
  2) Choose Compile or Decompile mode
  3) Compile: paste FDO source, press Run
  4) Decompile: choose File or Hex input, then Run
  5) Results show in tabs (Status, Hex, Source)

Shortcuts:
  - Cmd+Enter (macOS) / Ctrl+Enter (Win/Linux) to Run
  - Copy Hex for contiguous raw hex
  - Download buttons for binary/source output

-------------------------------------------------------------------------------
[07] API REFERENCE (ENDPOINTS)
-------------------------------------------------------------------------------
COMPILE FDO SOURCE

    $ curl -X POST http://localhost:8000/compile \
        -H "Content-Type: application/json" \
        -d '{
              "source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n    mat_object_id <test-001>\n  man_end_object <>\nuni_end_stream <>",
              "normalize": true
            }'

DECOMPILE FDO BINARY

    $ curl -X POST http://localhost:8000/decompile \
        -H "Content-Type: application/json" \
        -d '{
              "binary_data": "BASE64_ENCODED_BINARY_DATA",
              "format": "text"
            }'

HEALTH CHECK

    $ curl http://localhost:8000/health

GET EXAMPLES

    $ curl http://localhost:8000/examples

ENDPOINT SUMMARY

    +-----------+--------+----------------------------------------+
    | Endpoint  | Method | Description                            |
    +-----------+--------+----------------------------------------+
    | /health   |  GET   | Service health + daemon status         |
    | /compile  |  POST  | Compile source to binary               |
    | /decompile|  POST  | Decompile binary to source             |
    | /examples |  GET   | Retrieve available FDO examples        |
    +-----------+--------+----------------------------------------+

Note: Legacy split compilation endpoints were removed in v2.0.

-------------------------------------------------------------------------------
[08] ENVIRONMENT
-------------------------------------------------------------------------------
Container includes:
  - Python 3.11 base
  - Wine32 (for Windows executables)
  - FDO Daemon + required DLLs (Ada32.dll, Ada.bin, mfc42.dll)
  - Minimal runtime; no supervisord

-------------------------------------------------------------------------------
[09] PERFORMANCE NOTES
-------------------------------------------------------------------------------
Daemon-first design avoids process cold-start delays.
Practical impact observed:
  - Faster compilation (ms-level for warm requests)
  - Lower overhead via HTTP to a resident daemon
  - Direct Python integration for error handling and health checks

-------------------------------------------------------------------------------
[10] DEVELOPMENT / BACKEND DROP
-------------------------------------------------------------------------------
Revving the vendor backend:
  1) Replace contents under:
         releases/atomforge-backend/
     (Must include fdo_daemon.exe, fdo_compiler.exe, fdo_decompiler.exe,
      Ada32.dll, Ada.bin, mfc42.dll; see vendor docs.)
  2) Rebuild & restart:

         $ docker compose up --build -d

  The API selects the latest discovered backend automatically.

-------------------------------------------------------------------------------
[11] TESTING
-------------------------------------------------------------------------------
Suggested checks (examples):

    $ python3 test_fdo_tools.py          # FDO Tools integration tests
    $ ./validate_api_v2.sh               # API endpoint validation
    $ python3 test_golden_masters.py     # Golden master comparison

-------------------------------------------------------------------------------
[12] MIGRATION FROM v1.x
-------------------------------------------------------------------------------
- Added: Daemon-first HTTP integration
- Changed: `bin/` layout replaced by `releases/atomforge-backend/`
- Docker setup simplified

See MIGRATION.md if present.

-------------------------------------------------------------------------------
[13] TROUBLESHOOTING
-------------------------------------------------------------------------------
CONTAINER STARTUP

    $ docker logs atomforge
    $ docker exec atomforge wine --version

API DIAGNOSTICS

    $ curl http://localhost:8000/health

VERIFY BACKEND FILES

    $ docker exec atomforge ls -la /atomforge/releases/
    $ docker exec atomforge ls -la /atomforge/releases/atomforge-backend/

DAEMON CHECK (manual)

    $ docker exec atomforge \
        wine /atomforge/releases/atomforge-backend/fdo_daemon.exe --port 8080

PERFORMANCE CHECK

    $ python3 test_golden_masters.py --performance
    $ curl -s http://localhost:8000/health | jq '.execution_mode'

-------------------------------------------------------------------------------
[14] LICENSE
-------------------------------------------------------------------------------
MIT License. See `LICENSE` for details.
Note: This project relies on vendor components (e.g., Ada32.dll). Users are
responsible for compliance with any third-party terms.

-------------------------------------------------------------------------------
[15] NOTES
-------------------------------------------------------------------------------
Use AtomForge for legitimate reverse engineering and analysis only. The vendor
components are required for operation and are not redistributed here.

                -- end of file --
===============================================================================
