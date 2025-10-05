================================================================================
                         ATOMFORGE BACKEND v2.0
           Field Data Object Compiler/Decompiler REST API
================================================================================

OVERVIEW

  AtomForge Backend provides HTTP REST API access to Field Data Object (FDO)
  compilation and decompilation services. FDO files are used in AOL Database
  systems for structured data storage and retrieval.

  The backend integrates with Ada32.dll via a persistent daemon process to
  provide professional-grade FDO processing capabilities for reverse
  engineering, analysis, and development of AOL Database applications.


DEPLOYMENT

  Docker (Recommended)
  --------------------
  $ docker build -t atomforge .
  $ docker run -d -p 8000:8000 atomforge

  Docker Compose
  --------------
  $ docker-compose up -d

  The API server will be available at http://localhost:8000


API ENDPOINTS

  Health Check
  ------------
  GET /health

  Response:
    {
      "status": "healthy",
      "service": "atomforge-fdo-api",
      "version": "2.0.0",
      "daemon": {
        "health": {...},
        "crash_count": 0,
        "ready": true
      }
    }


  Compile FDO Source
  ------------------
  POST /compile
  Content-Type: application/json

  Request:
    {
      "source": "uni_start_stream <00x>\n...",
      "normalize": true
    }

  Response:
    Binary FDO data (application/octet-stream)
    Headers:
      X-Compilation-Time: execution time in seconds
      X-Output-Size: output size in bytes

  Error Response (400/422/500):
    {
      "success": false,
      "error": "error description",
      "daemon": {
        "normalized": {
          "message": "Ada32 error description",
          "code": "0x2F0006",
          "line": 15,
          "column": 23,
          "kind": "Missing Quote",
          "context": ["line context..."],
          "hint": "suggested fix"
        }
      }
    }


  Decompile FDO Binary
  --------------------
  POST /decompile
  Content-Type: application/json

  Request:
    {
      "binary_data": "base64_encoded_binary_data",
      "format": "text"
    }

  Response:
    {
      "success": true,
      "source": "decompiled FDO source code",
      "input_size": 1024,
      "output_size": 2048,
      "decompilation_time": "0.045s"
    }


  Chunk FDO for P3 Protocol
  --------------------------
  POST /compile-chunk
  Content-Type: application/json

  Request:
    {
      "source": "FDO script content",
      "token": "AT",
      "stream_id": 0,
      "validate_first": true
    }

  Supported tokens: AT, at, At, f1, ff, DD, D3, OT, XS

  Response:
    {
      "success": true,
      "chunks": ["base64_chunk1", "base64_chunk2"],
      "chunk_info": [
        {
          "payload": "base64_payload",
          "size": 512,
          "is_continuation": false,
          "sequence_index": 0
        }
      ],
      "chunk_count": 2,
      "total_size": 1024,
      "stats": {...}
    }


  Detect FDO in P3 Frame
  ----------------------
  POST /detect-fdo
  Content-Type: application/json

  Request:
    {
      "p3_frame": "base64_encoded_p3_frame"
    }

  Response:
    {
      "success": true,
      "fdo_detected": true,
      "p3_frame_valid": true,
      "p3_metadata": {
        "token": "AT",
        "stream_id": 123,
        "total_size": 1024
      },
      "fdo_metadata": {
        "token": "AT",
        "stream_id": 123,
        "fdo_size": 980
      },
      "fdo_data": "base64_fdo_binary",
      "summary": "FDO detected: AT stream 123"
    }


  Process JSONL P3 Logs
  ---------------------
  POST /decompile-jsonl
  Content-Type: multipart/form-data

  Upload .jsonl file containing P3 frame logs

  Response:
    {
      "success": true,
      "source": "decompiled FDO source",
      "frames_processed": 100,
      "fdo_frames_found": 50,
      "total_fdo_bytes": 51200,
      "chronological_order": "oldest_first",
      "supported_tokens": ["AT", "DD"],
      "decompilation_time": "1.234s",
      "frames_decompiled_successfully": 48,
      "frames_failed_decompilation": 2,
      "decompilation_failure_rate": 4.0,
      "killer_frames_count": 1,
      "daemon_restarts": 1
    }


  Get Example FDO Files
  ---------------------
  GET /examples?search=query

  Response:
    [
      {
        "name": "example.txt",
        "source": "FDO source code...",
        "size": 1024
      }
    ]


  File Management
  ---------------
  GET    /files                      List saved scripts
  GET    /files/recent?limit=10      Get recent scripts
  GET    /files/{id}                 Get specific script
  POST   /files                      Save new script
  PUT    /files/{id}                 Update script
  DELETE /files/{id}                 Delete script
  POST   /files/{id}/duplicate       Duplicate script
  PUT    /files/{id}/favorite        Toggle favorite status

  Script object:
    {
      "id": 1,
      "name": "script name",
      "content": "FDO source code",
      "created_at": "2025-10-05T12:00:00",
      "updated_at": "2025-10-05T12:00:00",
      "is_favorite": false,
      "content_length": 1024
    }


ERROR HANDLING

  HTTP Status Codes
  -----------------
  200  Success
  400  Bad Request - Syntax errors with line/column information
  404  Not Found - Resource not found
  409  Conflict - Name collision
  422  Unprocessable Entity - Semantic errors in valid syntax
  500  Internal Server Error - System errors and API failures

  Error Response Format
  ---------------------
  All error responses include structured JSON with detailed diagnostics:

    {
      "success": false,
      "error": "error description",
      "details": {...},
      "daemon": {
        "normalized": {
          "message": "descriptive error message",
          "code": "0x2F0006",
          "line": 15,
          "column": 23,
          "kind": "error type",
          "context": [
            "  13 | uni_start_stream <00x>",
            "  14 |   man_start_object <independent, \"Object Name>",
            ">>15 |     mat_object_id <32-105",
            "  16 |     mat_orientation <vcf>",
            "  17 |   man_end_object"
          ],
          "hint": "suggested fix"
        }
      }
    }

  Ada32 Crash Handling
  --------------------
  When Ada32.dll crashes (SIGSEGV, SIGFPE, SIGILL), the daemon gracefully
  handles the crash and returns error code 0xfffffc18 with crash details.
  The health endpoint reports crash_count for monitoring.


FDO FILE FORMATS

  Source Format (.txt files)
  ---------------------------
  Human-readable structured text with commands:

    uni_start_stream <00x>
      man_start_object <independent, "Object Name">
        mat_object_id <32-105>
        mat_orientation <vcf>
        act_set_criterion <07x>
      man_end_object
    uni_end_stream <>

  Binary Format (.str files)
  ---------------------------
  Official AOL binary format from .IDX database systems. Compiled FDO files
  are in this format.


P3 PROTOCOL INTEGRATION

  Chunking
  --------
  The /compile-chunk endpoint implements AOLBUF.AOL chunking logic for
  splitting FDO streams into P3 protocol payloads. Each chunk is sized to
  fit within P3 frame limits, with continuation bit support.

  Detection
  ---------
  The /detect-fdo endpoint automatically detects FDO data within P3 frames
  by analyzing frame structure and token patterns. Useful for real-time
  protocol analysis and auto-extraction.

  JSONL Processing
  ----------------
  The /decompile-jsonl endpoint processes log files containing P3 frames,
  extracts FDO data, reassembles streams chronologically, and decompiles
  the result. Handles multi-stream logs with different token types.


SAMPLE FILES

  The samples/ directory contains 252 real-world FDO files from production
  AOL systems:

    251 .txt files - FDO source format
    251 .bin files - FDO binary format (.str from .IDX databases)

  These samples are available via the /examples API endpoint and can be used
  for integration testing, error handling validation, and performance testing.


INTEGRATION BEST PRACTICES

  1. Connection Pooling
     Use persistent HTTP connections for multiple operations. The daemon
     runs continuously and handles concurrent requests.

  2. Error Handling
     Parse the structured error response for line/column information.
     Display context lines to users for syntax errors.

  3. Validation
     Use validate_first=true with /compile-chunk to catch errors before
     chunking operations.

  4. Health Monitoring
     Check /health endpoint periodically. Monitor crash_count and ready
     status for daemon health.

  5. Timeouts
     Set appropriate timeouts for large files. Decompilation typically
     completes in milliseconds, but complex files may take seconds.


DAEMON ARCHITECTURE

  The backend uses a persistent fdo_daemon.exe process (running under Wine)
  managed by the Python API server. This provides:

    - Low-latency operations (no per-request process spawn)
    - Connection pooling and concurrent request handling
    - Graceful crash recovery with automatic restart
    - Health monitoring and crash reporting

  The daemon communicates via HTTP:
    POST /compile    text/plain -> application/octet-stream
    POST /decompile  application/octet-stream -> text/plain
    GET  /health     health status


TECHNICAL SPECIFICATIONS

  API Framework: FastAPI 0.116.1
  Python: 3.13+
  Daemon Runtime: Wine (for Windows .exe execution)
  Database: SQLite (for file management)
  Container: Docker with Wine support


LICENSE

  MIT License. See LICENSE file for details.


SUPPORT

  For API integration issues:
    - Check /health endpoint for daemon status
    - Review error response normalized field for Ada32 details
    - Monitor crash_count for stability issues

  For protocol integration:
    - Use /detect-fdo for automatic FDO detection
    - Reference samples/ directory for valid FDO patterns
    - Test with /examples endpoint data

================================================================================
                    AtomForge Backend - AOL Database Tools
================================================================================