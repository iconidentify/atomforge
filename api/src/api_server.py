#!/usr/bin/env python3
"""
AtomForge API Server v2.0
Modern implementation using FDO Tools Python module
"""

import os
import sys
import time
import json
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, File, UploadFile, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
import json

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import FDO Tools manager
from fdo_tools_manager import get_fdo_tools_manager
from fdo_daemon_manager import FdoDaemonManager
from fdo_daemon_client import FdoDaemonClient, FdoDaemonError
from fdo_daemon_pool_manager import FdoDaemonPoolManager
from fdo_daemon_pool_client import FdoDaemonPoolClient

# Import file management
from database import init_database, test_database_connection
from file_manager import FileManager, Script

# Import chunking functionality
from fdo_chunker import FdoChunker, FdoChunkingError

# Import P3 frame parsing and FDO detection
from p3_frame_parser import P3FrameParser, P3FrameParseError
from fdo_detector import FdoDetector, FdoDetectionError

# Import JSONL processing
from jsonl_processor import JsonlProcessor, JsonlProcessingError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AtomForge FDO API v2.0",
    description="Field Data Object Compiler & Decompiler API using FDO Tools Python module",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers and clients
fdo_tools_manager = None
daemon_manager = None
daemon_client = None
pool_manager = None  # For pool mode
execution_mode = "single_daemon"  # "single_daemon" or "daemon_pool"


# Pydantic models
class CompileRequest(BaseModel):
    source: str
    normalize: bool = True


# Removed split request (not supported)


class DecompileRequest(BaseModel):
    binary_data: str  # Base64 encoded
    format: str = "text"


class ExampleResponse(BaseModel):
    name: str
    source: str
    size: int


# File Management Models
class SaveScriptRequest(BaseModel):
    name: str
    content: str
    script_id: Optional[int] = None


class ScriptResponse(BaseModel):
    id: int
    name: str
    content: str
    created_at: str
    updated_at: str
    is_favorite: bool
    content_length: int


class ScriptListResponse(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str
    is_favorite: bool
    content_length: int


class DuplicateScriptRequest(BaseModel):
    new_name: Optional[str] = None


# Chunking models
class CompileChunkRequest(BaseModel):
    source: str                    # FDO script content
    token: str = "AT"             # 2-byte token (AT, at, At, f1, ff, DD, D3, OT, XS)
    stream_id: int = 0            # Stream identifier
    validate_first: bool = True   # Pre-validate entire script


class ChunkInfo(BaseModel):
    """Information about a single P3 payload chunk"""
    payload: str                            # Base64-encoded P3 payload
    size: int                              # Payload size in bytes
    is_continuation: bool                  # True if this chunk needs P3 continuation bit (0x80)
    sequence_index: int                    # Position in the sequence (0-based)


class CompileChunkResponse(BaseModel):
    success: bool
    chunks: Optional[List[str]] = None      # Base64-encoded P3 payload chunks (legacy)
    chunk_info: Optional[List[ChunkInfo]] = None  # Enhanced chunk metadata with continuation info
    chunk_count: int = 0
    total_size: int = 0                     # Total bytes across all chunks
    validation_result: Optional[Dict] = None  # If validate_first=True
    stats: Optional[Dict] = None            # Chunking statistics
    error: Optional[str] = None             # Error message if failed


# P3 FDO Detection models
class DetectFdoRequest(BaseModel):
    p3_frame: str                           # Base64-encoded complete P3 frame


class DetectFdoResponse(BaseModel):
    success: bool                           # Whether P3 frame parsing succeeded
    fdo_detected: bool = False              # Whether FDO data was found
    p3_frame_valid: bool = False            # Whether P3 frame structure is valid
    error: Optional[str] = None             # Error message if parsing failed
    p3_metadata: Optional[Dict] = None      # P3 frame information
    fdo_metadata: Optional[Dict] = None     # FDO payload information (if detected)
    fdo_data: Optional[str] = None          # Base64-encoded raw FDO data (if detected)
    summary: Optional[str] = None           # Human-readable detection summary


# JSONL Processing models
class JsonlProcessResponse(BaseModel):
    success: bool                           # Whether JSONL processing succeeded
    source: Optional[str] = None            # Decompiled FDO source code
    frames_processed: int = 0               # Total number of frames parsed
    fdo_frames_found: int = 0               # Number of frames containing FDO data
    total_fdo_bytes: int = 0                # Total bytes of extracted FDO data
    chronological_order: str = "unknown"   # "oldest_first" or "newest_first"
    supported_tokens: List[str] = []        # List of token types found
    error: Optional[str] = None             # Error message if processing failed
    decompilation_time: Optional[str] = None # Time taken for decompilation
    frames_decompiled_successfully: int = 0  # Number of frames successfully decompiled
    frames_failed_decompilation: int = 0     # Number of frames that failed decompilation
    decompilation_failure_rate: Optional[float] = None  # Percentage of frames that failed
    killer_frames_count: int = 0            # Number of frames that crashed daemon
    daemon_restarts: int = 0                # Number of times daemon was restarted
    frames_skipped_after_crash: int = 0     # Number of frames skipped due to unrecoverable crashes


# --- Helpers ---
def _looks_banner_line(line: str) -> bool:
    s = (line or "").strip()
    if not s:
        return True  # drop leading empty lines
    u = s.upper()
    if "GID" in u and ("<<" in s or ">>" in s):
        return True
    return False


def sanitize_fdo_source(text: str) -> str:
    """Strip non-FDO banner/header lines (e.g., GID banners) from the top of source."""
    lines = text.splitlines()
    # Remove leading blanks and one or more banner lines
    removed_any = False
    while lines and _looks_banner_line(lines[0]):
        removed_any = True
        lines.pop(0)
    return "\n".join(lines) if removed_any else text


def _normalize_daemon_error_json(json_obj: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if isinstance(json_obj, dict) and "error" in json_obj and isinstance(json_obj["error"], dict):
            err = json_obj["error"]
            # Ensure only expected keys
            return {
                "message": err.get("message"),
                "code": err.get("code"),
                "line": err.get("line"),
                "kind": err.get("kind"),
                "context": err.get("context"),
                "hint": err.get("hint"),
            }
    except Exception:
        pass
    return {}


def _normalize_daemon_error_text(text: str) -> Dict[str, Any]:
    import re
    if not text:
        return {}
    msg = None
    code = None
    line = None
    kind = None
    hint = None
    try:
        m = re.search(r'"message"\s*:\s*"([\s\S]*?)"', text)
        if m:
            msg = m.group(1)
        m = re.search(r'"code"\s*:\s*"([^"]+)"', text)
        if m:
            code = m.group(1)
        m = re.search(r'"line"\s*:\s*(\d+)', text)
        if m:
            line = int(m.group(1))
        m = re.search(r'"kind"\s*:\s*"([^"]*)"', text)
        if m:
            kind = m.group(1)
        m = re.search(r'"hint"\s*:\s*"([\s\S]*?)"', text)
        if m:
            hint = m.group(1)
        context: list[str] = []
        for ln in text.splitlines():
            s = ln.strip().strip(',')
            if re.match(r'^"?(>>\s*)?\d+\s\|\s', s):
                s2 = s.strip('"')
                context.append(s2)
        return {
            "message": msg,
            "code": code,
            "line": line,
            "kind": kind,
            "context": context or None,
            "hint": hint,
        }
    except Exception:
        return {}


def _build_daemon_error_detail(daemon_content_type: str, daemon_text: str, daemon_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # Prefer JSON when available
    err = {}
    if daemon_json:
        err = _normalize_daemon_error_json(daemon_json)
    if not err and daemon_text:
        err = _normalize_daemon_error_text(daemon_text)

    # Clean Ada32 prefix for headline message and detect crash types
    msg = err.get("message") or ""
    code = err.get("code") or ""

    if msg:
        import re
        # Detect new daemon crash error codes
        if code == "0xfffffc18" or "Ada32 crashed:" in msg:
            # This is a graceful crash response from new daemon
            # Keep the crash message as-is for visibility
            err["crash_type"] = "ada32_crash_handled"
            if "Segmentation fault" in msg:
                err["crash_signal"] = "SIGSEGV"
            elif "Floating point exception" in msg:
                err["crash_signal"] = "SIGFPE"
            elif "Illegal instruction" in msg:
                err["crash_signal"] = "SIGILL"
        else:
            # Normal Ada32 error - clean the prefix
            msg = re.sub(r'^Ada32\s+error\s+rc=[^:]+:\s*', '', msg, flags=re.I).strip()
            err["message"] = msg

    return err

@app.on_event("startup")
async def startup_event():
    """Initialize FDO Tools on startup"""
    global fdo_tools_manager, daemon_manager, daemon_client, pool_manager, execution_mode

    # Detect pool mode from environment
    pool_enabled = os.getenv("FDO_DAEMON_POOL_ENABLED", "false").lower() == "true"
    execution_mode = "daemon_pool" if pool_enabled else "single_daemon"

    logger.info(f"🚀 Starting AtomForge API Server v2.0 (mode: {execution_mode})")

    try:
        # Initialize database
        if not init_database():
            raise RuntimeError("Failed to initialize database")

        if not test_database_connection():
            raise RuntimeError("Database connection test failed")

        logger.info("📦 Database initialized successfully")

        # Initialize manager and discover releases/backends
        fdo_tools_manager = get_fdo_tools_manager()
        releases = fdo_tools_manager.discover_releases()
        logger.info(f"Found FDO releases/backends: {list(releases.keys())}")

        selected_release = fdo_tools_manager.select_latest_release()
        if not selected_release:
            raise RuntimeError("No FDO releases/backends found")

        # Get daemon executable path
        daemon_exe = fdo_tools_manager.get_daemon_exe_path()
        if not daemon_exe:
            raise RuntimeError("fdo_daemon.exe not found in selected release or backend drop")

        bind = os.getenv("FDO_DAEMON_BIND", "127.0.0.1")
        token = os.getenv("FDO_DAEMON_TOKEN")

        if pool_enabled:
            # Pool mode - start multiple daemons
            pool_size = int(os.getenv("FDO_DAEMON_POOL_SIZE", "5"))
            base_port = int(os.getenv("FDO_DAEMON_POOL_BASE_PORT", "8080"))
            health_interval = float(os.getenv("FDO_DAEMON_HEALTH_INTERVAL", "10.0"))
            restart_delay = float(os.getenv("FDO_DAEMON_RESTART_DELAY", "2.0"))
            max_restart_attempts = int(os.getenv("FDO_DAEMON_MAX_RESTART_ATTEMPTS", "5"))
            max_retries = int(os.getenv("FDO_DAEMON_MAX_RETRIES", "3"))
            request_timeout = float(os.getenv("FDO_DAEMON_REQUEST_TIMEOUT", "10.0"))
            circuit_breaker_threshold = int(os.getenv("FDO_DAEMON_CIRCUIT_BREAKER_THRESHOLD", "3"))

            logger.info(f"🔧 Pool configuration: size={pool_size}, ports={base_port}-{base_port + pool_size - 1}")

            pool_manager = FdoDaemonPoolManager(
                exe_path=daemon_exe,
                pool_size=pool_size,
                base_port=base_port,
                bind_host=bind,
                restart_delay=restart_delay,
                health_interval=health_interval,
                max_restart_attempts=max_restart_attempts,
                circuit_breaker_threshold=circuit_breaker_threshold
            )
            pool_manager.start()

            daemon_client = FdoDaemonPoolClient(
                pool_manager=pool_manager,
                max_retries=max_retries,
                timeout_seconds=request_timeout
            )

            # Confirm pool health
            health = daemon_client.health()
            logger.info(f"📡 Daemon pool health: {health}")

        else:
            # Single daemon mode (backward compatible)
            port_env = os.getenv("FDO_DAEMON_PORT", "0")
            port = int(port_env) if port_env.isdigit() else 0

            daemon_manager = FdoDaemonManager(
                exe_path=daemon_exe,
                bind_host=bind,
                port=(port or None),
            )
            daemon_manager.start()

            daemon_client = FdoDaemonClient(base_url=daemon_manager.base_url, token=token)

            # Confirm health
            health = daemon_client.health()
            logger.info(f"📡 Single daemon health: {health}")

    except Exception as e:
        logger.error(f"Failed to initialize FDO Tools: {e}")
        raise


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint with pool mode support"""
    try:
        release_info = fdo_tools_manager.get_release_info()
        health = daemon_client.health()

        response = {
            "service": "atomforge-fdo-api",
            "version": "2.0.0",
            "features": [
                "compilation",
                "decompilation"
            ],
            "execution_mode": execution_mode,
            "release": {
                "path": release_info.get("path"),
                "bin_dir": release_info.get("bin_dir"),
            }
        }

        if execution_mode == "daemon_pool":
            # Pool mode health
            pool_healthy = health.get("healthy", False)
            instances_healthy = health.get("instances_healthy", 0)
            pool_size = health.get("pool_size", 0)

            response["status"] = "healthy" if pool_healthy else "degraded"
            response["pool"] = {
                "enabled": True,
                "size": pool_size,
                "healthy_instances": instances_healthy,
                "health_percentage": health.get("pool_health_percentage", 0)
            }
        else:
            # Single daemon mode
            crash_count = health.get("crash_count", 0) if isinstance(health, dict) else 0
            readiness = health.get("ready", True) if isinstance(health, dict) else True

            response["status"] = "healthy" if health and readiness else "degraded"
            response["daemon"] = {
                "base_url": daemon_manager.base_url,
                "bind": daemon_manager.bind_host,
                "port": daemon_manager.port,
                "health": health,
                "crash_count": crash_count,
                "ready": readiness,
            }

        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": "atomforge-fdo-api",
                "version": "2.0.0",
                "error": str(e)
            }
        )


@app.get("/health/pool")
async def pool_health_check():
    """Get detailed pool status and metrics (pool mode only)"""
    if execution_mode != "daemon_pool":
        return JSONResponse(
            status_code=400,
            content={
                "error": "Pool mode not enabled",
                "execution_mode": execution_mode
            }
        )

    try:
        pool_status = pool_manager.get_pool_status()
        return pool_status

    except Exception as e:
        logger.error(f"Pool health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health/pool/memory")
async def pool_memory_metrics():
    """Get per-daemon memory usage metrics"""
    if execution_mode != "daemon_pool":
        return JSONResponse(
            status_code=400,
            content={
                "error": "Pool mode not enabled",
                "execution_mode": execution_mode
            }
        )

    try:
        import psutil

        # Collect daemon processes
        daemon_procs = {}
        starter_procs = {}
        wine_infra = []

        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
            try:
                rss_mb = proc.info['memory_info'].rss / 1024 / 1024
                name = proc.info['name']
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''

                # Match daemon processes by port
                if 'fdo_daemon.exe' in cmdline:
                    # Extract port from command line
                    for i, arg in enumerate(proc.info['cmdline']):
                        if arg == '--port' and i + 1 < len(proc.info['cmdline']):
                            port = int(proc.info['cmdline'][i + 1])
                            daemon_procs[port] = rss_mb
                            break

                # Match launcher processes (start.exe with significant memory)
                elif name == 'start.exe' and rss_mb > 20:
                    # Associate with closest daemon (approximate by PID proximity)
                    starter_procs[proc.info['pid']] = rss_mb

                # Wine infrastructure
                elif 'wine' in name.lower() or name in ['services.exe', 'winedevice.exe', 'explorer.exe', 'plugplay.exe', 'svchost.exe', 'rpcss.exe']:
                    wine_infra.append(rss_mb)

            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                pass

        # Calculate averages
        avg_daemon_mem = sum(daemon_procs.values()) / len(daemon_procs) if daemon_procs else 0
        avg_starter_mem = sum(starter_procs.values()) / len(starter_procs) if starter_procs else 0
        total_wine_infra = sum(wine_infra)

        # Get pool size
        pool_size = pool_manager.pool_size
        wine_infra_per_daemon = total_wine_infra / pool_size if pool_size > 0 else 0

        # Calculate per-daemon total
        per_daemon_total = avg_daemon_mem + avg_starter_mem + wine_infra_per_daemon

        # Build per-instance metrics
        pool_status = pool_manager.get_pool_status()
        instances_memory = []
        for instance in pool_status['instances']:
            port = instance['port']
            daemon_mem = daemon_procs.get(port, avg_daemon_mem)
            instances_memory.append({
                'id': instance['id'],
                'port': port,
                'daemon_memory_mb': round(daemon_mem, 1),
                'launcher_memory_mb': round(avg_starter_mem, 1),
                'wine_infra_share_mb': round(wine_infra_per_daemon, 1),
                'total_memory_mb': round(daemon_mem + avg_starter_mem + wine_infra_per_daemon, 1)
            })

        return {
            'pool_size': pool_size,
            'avg_daemon_memory_mb': round(avg_daemon_mem, 1),
            'avg_launcher_memory_mb': round(avg_starter_mem, 1),
            'wine_infra_total_mb': round(total_wine_infra, 1),
            'wine_infra_per_daemon_mb': round(wine_infra_per_daemon, 1),
            'per_daemon_total_mb': round(per_daemon_total, 1),
            'instances': instances_memory
        }

    except Exception as e:
        logger.error(f"Failed to get pool memory metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/pool/reset-circuit-breakers")
async def reset_circuit_breakers():
    """Reset all circuit breakers in the pool"""
    if execution_mode != "daemon_pool":
        return JSONResponse(
            status_code=400,
            content={
                "error": "Pool mode not enabled",
                "execution_mode": execution_mode
            }
        )

    try:
        count = pool_manager.reset_circuit_breakers()
        return {
            "success": True,
            "circuit_breakers_reset": count,
            "message": f"Reset circuit breakers for {count} instance(s)"
        }

    except Exception as e:
        logger.error(f"Failed to reset circuit breakers: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )









@app.post("/compile")
async def compile_fdo(request: CompileRequest):
    """
    Compile FDO source code to binary format

    Returns:
        - Success: Binary FDO data as application/octet-stream
        - Error: JSON error response
    """
    try:
        # Validate input
        source = request.source.strip()
        if not source:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "Empty source code provided",
                    "details": {"field": "source"}
                }
            )

        # Compile using daemon (text/plain -> octet-stream)
        start_time = time.time()
        try:
            binary_data = daemon_client.compile_source(sanitize_fdo_source(source))
        except FdoDaemonError as e:
            # Single daemon error details with normalized error payload
            norm = _build_daemon_error_detail(e.content_type, e.text, e.json)
            raise HTTPException(
                status_code=e.status_code or 500,
                detail={
                    "success": False,
                    "error": "Daemon compilation error",
                    "daemon": {
                        "status_code": e.status_code,
                        "content_type": e.content_type,
                        "text": e.text,
                        "json": e.json,
                        "normalized": norm,
                    }
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail={"success": False, "error": "Daemon compilation error", "details": {"exception": str(e)}})
        duration = time.time() - start_time

        logger.info(f"Compilation successful: {len(binary_data)} bytes in {duration:.3f}s")

        # Return binary data
        return Response(
            content=binary_data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=compiled.fdo",
                "X-Compilation-Time": f"{duration:.3f}s",
                "X-Output-Size": str(len(binary_data))
            }
        )

    except Exception as e:
        logger.error(f"Compilation failed: {e}")
        # Preserve previously raised HTTPException (with daemon details)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error during compilation",
                "details": {"exception": str(e)}
            }
        )


# Split endpoint intentionally removed (not supported)


@app.post("/decompile")
async def decompile_fdo(request: DecompileRequest):
    """
    Decompile FDO binary data to source code

    Returns:
        - Success: JSON response with decompiled source
        - Error: JSON error response
    """
    try:
        # Decode base64 binary data
        try:
            binary_data = base64.b64decode(request.binary_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "Invalid base64 binary data",
                    "details": {"decode_error": str(e)}
                }
            )

        if not binary_data:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "Empty binary data provided"
                }
            )

        # Decompile using daemon (octet-stream -> text/plain)
        start_time = time.time()
        try:
            source_code_raw = daemon_client.decompile_binary(binary_data)
            # Unescape quotes that the FDO daemon may have escaped
            source_code = source_code_raw.replace('\\"', '"')
        except FdoDaemonError as e:
            norm = _build_daemon_error_detail(e.content_type, e.text, e.json)
            raise HTTPException(
                status_code=e.status_code or 500,
                detail={
                    "success": False,
                    "error": "Daemon decompilation error",
                    "daemon": {
                        "status_code": e.status_code,
                        "content_type": e.content_type,
                        "text": e.text,
                        "json": e.json,
                        "normalized": norm,
                    }
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail={"success": False, "error": "Daemon decompilation error", "details": {"exception": str(e)}})
        duration = time.time() - start_time

        logger.info(f"Decompilation successful: {len(source_code)} chars in {duration:.3f}s")

        return {
            "success": True,
            "source": source_code,
            "source_code": source_code,  # UI compatibility
            "format": request.format,
            "input_size": len(binary_data),
            "output_size": len(source_code),
            "decompilation_time": f"{duration:.3f}s"
        }

    except Exception as e:
        logger.error(f"Decompilation failed: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error during decompilation",
                "details": {"exception": str(e)}
            }
        )


@app.post("/decompile-jsonl", response_model=JsonlProcessResponse)
async def decompile_jsonl_file(file: UploadFile = File(...)):
    """
    Process JSONL file containing P3 frames to extract and decompile FDO streams.

    This endpoint analyzes JSONL logs of P3 protocol frames, extracts FDO data
    from frames with known token types, reassembles the streams chronologically,
    and decompiles the result to human-readable FDO source code.

    Args:
        file: Uploaded JSONL file containing P3 frame data

    Returns:
        JsonlProcessResponse with decompiled source and processing metadata
    """
    start_time = time.time()

    try:
        # Validate file type
        if not file.filename.lower().endswith('.jsonl'):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "File must have .jsonl extension",
                    "details": {"filename": file.filename}
                }
            )

        # Read file content and create line iterator for streaming processing
        try:
            content = await file.read()
            jsonl_content = content.decode('utf-8')
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "File must be valid UTF-8 encoded JSONL",
                    "details": {"decode_error": str(e)}
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "Failed to read uploaded file",
                    "details": {"read_error": str(e)}
                }
            )

        if not jsonl_content.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "JSONL file is empty"
                }
            )

        # Create line iterator factory for streaming processor
        def create_line_iterator():
            """Create line iterator that yields JSONL lines one at a time."""
            for line in jsonl_content.splitlines():
                if line.strip():  # Skip empty lines
                    yield line

        # Process JSONL file using streaming processor
        try:
            # Pass line iterator factory to allow multiple iterations
            processing_result = JsonlProcessor.stream_process_file(create_line_iterator)
        except JsonlProcessingError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": f"JSONL processing failed: {str(e)}"
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "Internal error during JSONL processing",
                    "details": {"exception": str(e)}
                }
            )

        # Check if processing found any FDO data
        if not processing_result['success']:
            return JsonlProcessResponse(
                success=False,
                frames_processed=processing_result['frames_processed'],
                fdo_frames_found=processing_result['fdo_frames_found'],
                total_fdo_bytes=processing_result['total_fdo_bytes'],
                chronological_order=processing_result['chronological_order'],
                supported_tokens=processing_result['supported_tokens'],
                error=processing_result['error']
            )

        # Decompile the extracted FDO frames individually
        fdo_frames = processing_result['fdo_frames']
        if not fdo_frames:
            return JsonlProcessResponse(
                success=False,
                frames_processed=processing_result['frames_processed'],
                fdo_frames_found=processing_result['fdo_frames_found'],
                total_fdo_bytes=0,
                chronological_order=processing_result['chronological_order'],
                supported_tokens=processing_result['supported_tokens'],
                error="No FDO data extracted from frames"
            )

        # Decompile frames individually using enhanced forensic approach with daemon restart capability
        decompile_start = time.time()
        try:
            # Pass daemon_manager for restart capability during crashes
            decompilation_result = JsonlProcessor._decompile_frames_individually(fdo_frames, daemon_client, daemon_manager)
            source_code = decompilation_result['source']
            frames_decompiled_successfully = decompilation_result['frames_decompiled_successfully']
            frames_failed_decompilation = decompilation_result['frames_failed_decompilation']
            decompilation_failure_rate = decompilation_result['decompilation_failure_rate']
            killer_frames = decompilation_result.get('killer_frames', [])
            daemon_restarts = decompilation_result.get('daemon_restarts', 0)
            frames_skipped_after_crash = decompilation_result.get('frames_skipped_after_crash', 0)
        except Exception as e:
            return JsonlProcessResponse(
                success=False,
                frames_processed=processing_result['frames_processed'],
                fdo_frames_found=processing_result['fdo_frames_found'],
                total_fdo_bytes=processing_result['total_fdo_bytes'],
                chronological_order=processing_result['chronological_order'],
                supported_tokens=processing_result['supported_tokens'],
                error=f"Frame-by-frame decompilation error: {str(e)}"
            )

        decompile_duration = time.time() - decompile_start
        total_duration = time.time() - start_time

        logger.info(f"Enhanced JSONL processing successful: {file.filename}, "
                   f"{processing_result['frames_processed']} frames, "
                   f"{processing_result['fdo_frames_found']} FDO frames, "
                   f"{frames_decompiled_successfully}/{processing_result['fdo_frames_found']} frames decompiled, "
                   f"{len(killer_frames)} killer frames, {daemon_restarts} daemon restarts, "
                   f"{frames_skipped_after_crash} frames skipped, "
                   f"{len(source_code)} chars, {decompilation_failure_rate:.1f}% failure rate, "
                   f"{total_duration:.3f}s")

        if killer_frames:
            logger.warning(f"🔥 {len(killer_frames)} KILLER FRAMES detected in {file.filename}!")
            for killer in killer_frames[:3]:  # Log first 3 killer frames
                logger.warning(f"   Killer Frame {killer['index']}: {killer['token']}/{killer['stream_id']} "
                             f"({killer['size_bytes']} bytes) - {killer['error']}")

        return JsonlProcessResponse(
            success=True,
            source=source_code,
            frames_processed=processing_result['frames_processed'],
            fdo_frames_found=processing_result['fdo_frames_found'],
            total_fdo_bytes=processing_result['total_fdo_bytes'],
            chronological_order=processing_result['chronological_order'],
            supported_tokens=processing_result['supported_tokens'],
            decompilation_time=f"{decompile_duration:.3f}s",
            frames_decompiled_successfully=frames_decompiled_successfully,
            frames_failed_decompilation=frames_failed_decompilation,
            decompilation_failure_rate=decompilation_failure_rate,
            killer_frames_count=len(killer_frames),
            daemon_restarts=daemon_restarts,
            frames_skipped_after_crash=frames_skipped_after_crash
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during JSONL processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error during JSONL processing",
                "details": {"exception": str(e)}
            }
        )


@app.post("/compile-chunk", response_model=CompileChunkResponse)
async def compile_chunk_fdo(request: CompileChunkRequest):
    """
    Chunk FDO script into P3-ready payload segments.

    This endpoint implements AOLBUF.AOL chunking logic for splitting FDO streams
    into properly sized P3 protocol payloads ready for transmission.

    Args:
        request: CompileChunkRequest with FDO script, token, stream_id, and options

    Returns:
        CompileChunkResponse with chunked payloads and metadata
    """
    start_time = time.time()

    try:
        # Initialize chunker with daemon client
        chunker = FdoChunker(daemon_client)

        # Perform chunking with optional validation
        result = await chunker.chunk_and_validate(
            fdo_script=request.source,
            stream_id=request.stream_id,
            token=request.token,
            validate_first=request.validate_first
        )

        # Convert binary chunks to base64 for JSON response
        base64_chunks = []
        chunk_info_list = []

        if result['success'] and result['chunks']:
            base64_chunks = [base64.b64encode(chunk).decode('ascii') for chunk in result['chunks']]

            # Build enhanced chunk info with continuation metadata
            for i, (chunk, info) in enumerate(zip(result['chunks'], result['chunk_info'])):
                chunk_info_list.append(ChunkInfo(
                    payload=base64.b64encode(chunk).decode('ascii'),
                    size=info['size'],
                    is_continuation=info['is_continuation'],
                    sequence_index=info['sequence_index']
                ))

        # Build response
        response = CompileChunkResponse(
            success=result['success'],
            chunks=base64_chunks if result['success'] else None,  # Legacy compatibility
            chunk_info=chunk_info_list if result['success'] else None,  # Enhanced metadata
            chunk_count=len(base64_chunks) if result['success'] else 0,
            total_size=result['stats'].get('total_size', 0) if result['success'] else 0,
            validation_result=result.get('validation'),
            stats=result.get('stats'),
            error=result.get('error')
        )

        duration = time.time() - start_time

        if result['success']:
            logger.info(f"FDO chunking successful: {len(base64_chunks)} chunks, "
                       f"{result['stats']['total_size']} bytes, {duration:.3f}s")
        else:
            logger.warning(f"FDO chunking failed: {result.get('error', 'Unknown error')}")

        return response

    except FdoChunkingError as e:
        logger.error(f"Chunking error: {e}")
        return CompileChunkResponse(
            success=False,
            error=f"Chunking failed: {str(e)}"
        )

    except ValueError as e:
        logger.error(f"Invalid chunking parameters: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "Invalid request parameters",
                "details": {"validation_error": str(e)}
            }
        )

    except Exception as e:
        logger.error(f"Unexpected chunking error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal chunking error",
                "details": {"exception": str(e)}
            }
        )


@app.post("/detect-fdo", response_model=DetectFdoResponse)
async def detect_fdo_in_p3_frame(request: DetectFdoRequest):
    """
    Detect and extract FDO data from a complete P3 frame.

    This endpoint analyzes a P3 protocol frame to automatically detect if it contains
    valid FDO (Field Data Object) data. Designed for real-time UI hints and auto-extraction.

    Args:
        request: DetectFdoRequest with base64-encoded P3 frame

    Returns:
        DetectFdoResponse with detection results and extracted FDO data if found
    """
    start_time = time.time()

    try:
        logger.debug(f"Processing P3 frame detection request: {len(request.p3_frame)} base64 chars")

        # Perform FDO detection using the detection engine
        detection_result = FdoDetector.detect_from_base64(request.p3_frame)

        # Generate human-readable summary
        summary = FdoDetector.get_detection_summary(detection_result)

        # Build comprehensive response
        response = DetectFdoResponse(
            success=detection_result['success'],
            fdo_detected=detection_result['fdo_detected'],
            p3_frame_valid=detection_result['p3_frame_valid'],
            error=detection_result.get('error'),
            p3_metadata=detection_result.get('p3_metadata'),
            fdo_metadata=detection_result.get('fdo_metadata'),
            fdo_data=detection_result.get('fdo_data'),
            summary=summary
        )

        duration = time.time() - start_time

        if detection_result['fdo_detected']:
            meta = detection_result['fdo_metadata']
            logger.info(f"P3 FDO detection successful: token={meta.get('token')}, "
                       f"stream_id={meta.get('stream_id')}, fdo_size={meta.get('fdo_size')} bytes, "
                       f"duration={duration:.3f}s")
        else:
            logger.debug(f"P3 FDO detection completed: {summary}, duration={duration:.3f}s")

        return response

    except FdoDetectionError as e:
        logger.error(f"FDO detection error: {e}")
        return DetectFdoResponse(
            success=False,
            fdo_detected=False,
            p3_frame_valid=False,
            error=f"Detection failed: {str(e)}",
            summary="FDO detection failed"
        )

    except Exception as e:
        logger.error(f"Unexpected error during P3 FDO detection: {e}", exc_info=True)
        return DetectFdoResponse(
            success=False,
            fdo_detected=False,
            p3_frame_valid=False,
            error=f"Internal server error: {str(e)}",
            summary="Internal error during detection"
        )


@app.get("/examples", response_model=List[ExampleResponse])
async def get_examples(search: str = None):
    """Get available FDO examples from golden tests, optionally filtered by search query
    
    Args:
        search: Optional search query to filter examples by content or filename
    """
    try:
        # Prefer vendor-provided samples under the selected backend drop
        release_info = fdo_tools_manager.get_release_info()
        samples_dir = os.path.join(release_info["path"], "samples")

        # Backward-compatible fallbacks
        if not os.path.exists(samples_dir):
            legacy_examples = os.path.join(release_info["path"], "examples")
            samples_dir = legacy_examples if os.path.exists(legacy_examples) else "bin/fdo_compiler_decompiler/golden_tests_immutable"

        examples = []

        if os.path.exists(samples_dir):
            txt_paths = sorted(Path(samples_dir).glob("*.txt"), key=lambda p: p.name.lower())
            for file_path in txt_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Apply search filter if provided
                    if search:
                        search_lower = search.lower()
                        # Search in both filename and content (case-insensitive)
                        if search_lower not in file_path.name.lower() and search_lower not in content.lower():
                            continue

                    examples.append(ExampleResponse(
                        name=file_path.name,
                        source=content,
                        size=len(content)
                    ))
                except Exception as e:
                    logger.warning(f"Failed to load example {file_path}: {e}")

        # If no examples found, provide a basic one
        if not examples and not search:
            examples.append(ExampleResponse(
                name="basic_example.txt",
                source="uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n    mat_object_id <test-001>\n  man_end_object <>\nuni_end_stream <>",
                size=120
            ))

        logger.info(f"Loaded {len(examples)} FDO examples from {samples_dir}" + (f" (filtered by '{search}')" if search else ""))
        return examples

    except Exception as e:
        logger.error(f"Failed to load examples: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load examples: {str(e)}"
        )


# File Management Endpoints

@app.get("/files", response_model=List[ScriptListResponse])
async def list_scripts(search: str = None, favorites_only: bool = False):
    """List all saved scripts, optionally filtered by search term or favorites"""
    try:
        scripts = FileManager.list_scripts(search=search, favorites_only=favorites_only)

        # Convert to list response format (exclude content for performance)
        script_list = []
        for script in scripts:
            script_list.append(ScriptListResponse(
                id=script.id,
                name=script.name,
                created_at=script.created_at,
                updated_at=script.updated_at,
                is_favorite=script.is_favorite,
                content_length=len(script.content) if script.content else 0
            ))

        logger.info(f"Listed {len(script_list)} scripts (search: {search}, favorites: {favorites_only})")
        return script_list

    except Exception as e:
        logger.error(f"Failed to list scripts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list scripts: {str(e)}")


@app.get("/files/recent", response_model=List[ScriptListResponse])
async def get_recent_scripts(limit: int = 10):
    """Get recently updated scripts"""
    try:
        if limit > 50:
            limit = 50  # Cap at 50 for performance

        scripts = FileManager.get_recent_scripts(limit=limit)

        # Convert to list response format
        script_list = []
        for script in scripts:
            script_list.append(ScriptListResponse(
                id=script.id,
                name=script.name,
                created_at=script.created_at,
                updated_at=script.updated_at,
                is_favorite=script.is_favorite,
                content_length=len(script.content) if script.content else 0
            ))

        logger.info(f"Retrieved {len(script_list)} recent scripts")
        return script_list

    except Exception as e:
        logger.error(f"Failed to get recent scripts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent scripts: {str(e)}")


@app.get("/files/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: int):
    """Get a specific script by ID"""
    try:
        script = FileManager.get_script(script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        return ScriptResponse(**script.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get script: {str(e)}")


@app.post("/files", response_model=ScriptResponse)
async def save_script(request: SaveScriptRequest):
    """Save a new script or update an existing one"""
    try:
        # Validate script name
        if not request.name.strip():
            raise HTTPException(status_code=400, detail="Script name cannot be empty")

        if len(request.name) > 100:
            raise HTTPException(status_code=400, detail="Script name too long (max 100 characters)")

        script = FileManager.save_script(
            name=request.name.strip(),
            content=request.content,
            script_id=request.script_id
        )

        if not script:
            raise HTTPException(status_code=500, detail="Failed to save script")

        logger.info(f"Saved script: {script.name} (ID: {script.id})")
        return ScriptResponse(**script.to_dict())

    except ValueError as e:
        # Handle unique constraint violations
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save script: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save script: {str(e)}")


@app.put("/files/{script_id}", response_model=ScriptResponse)
async def update_script(script_id: int, request: SaveScriptRequest):
    """Update an existing script"""
    try:
        # Validate script exists
        existing_script = FileManager.get_script(script_id)
        if not existing_script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Validate script name
        if not request.name.strip():
            raise HTTPException(status_code=400, detail="Script name cannot be empty")

        if len(request.name) > 100:
            raise HTTPException(status_code=400, detail="Script name too long (max 100 characters)")

        script = FileManager.save_script(
            name=request.name.strip(),
            content=request.content,
            script_id=script_id
        )

        if not script:
            raise HTTPException(status_code=500, detail="Failed to update script")

        logger.info(f"Updated script: {script.name} (ID: {script_id})")
        return ScriptResponse(**script.to_dict())

    except ValueError as e:
        # Handle unique constraint violations
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update script: {str(e)}")


@app.delete("/files/{script_id}")
async def delete_script(script_id: int):
    """Delete a script by ID"""
    try:
        success = FileManager.delete_script(script_id)
        if not success:
            raise HTTPException(status_code=404, detail="Script not found")

        logger.info(f"Deleted script ID: {script_id}")
        return {"success": True, "message": "Script deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete script: {str(e)}")


@app.post("/files/{script_id}/duplicate", response_model=ScriptResponse)
async def duplicate_script(script_id: int, request: DuplicateScriptRequest):
    """Duplicate an existing script"""
    try:
        script = FileManager.duplicate_script(script_id, request.new_name)
        if not script:
            raise HTTPException(status_code=404, detail="Original script not found")

        logger.info(f"Duplicated script ID {script_id} as: {script.name} (ID: {script.id})")
        return ScriptResponse(**script.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to duplicate script: {str(e)}")


@app.put("/files/{script_id}/favorite")
async def toggle_favorite(script_id: int):
    """Toggle favorite status of a script"""
    try:
        new_status = FileManager.toggle_favorite(script_id)
        if new_status is None:
            raise HTTPException(status_code=404, detail="Script not found")

        logger.info(f"Toggled favorite for script ID {script_id}: {new_status}")
        return {"success": True, "is_favorite": new_status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle favorite for script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle favorite: {str(e)}")


# Pool monitoring UI endpoint
@app.get("/pool")
async def get_pool_ui():
    """Serve the pool monitoring UI"""
    static_dir = Path(__file__).parent.parent / "static"
    pool_html = static_dir / "pool.html"

    if not pool_html.exists():
        raise HTTPException(status_code=404, detail="Pool monitoring UI not found")

    return FileResponse(pool_html)


# Mount static files (web interface)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"📁 Mounted static files from: {static_dir}")


def main():
    """Main entry point"""
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    logger.info(f"🚀 Starting AtomForge API Server v2.0 (daemon-only)")
    logger.info(f"   Server: http://{host}:{port}")
    logger.info(f"   Docs:   http://{host}:{port}/docs")
    logger.info(f"   Health: http://{host}:{port}/health")

    # Run server
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=False,
        access_log=True
    )


if __name__ == "__main__":
    main()