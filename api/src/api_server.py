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

from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import FDO Tools manager
from fdo_tools_manager import get_fdo_tools_manager
from fdo_daemon_manager import FdoDaemonManager
from fdo_daemon_client import FdoDaemonClient, FdoDaemonError

# Import file management
from database import init_database, test_database_connection
from file_manager import FileManager, Script

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

# Global daemon manager/client
fdo_tools_manager = None
daemon_manager = None
daemon_client = None


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
    # Clean Ada32 prefix for headline message
    msg = err.get("message") or ""
    if msg:
        import re
        msg = re.sub(r'^Ada32\s+error\s+rc=[^:]+:\s*', '', msg, flags=re.I).strip()
        err["message"] = msg
    return err

@app.on_event("startup")
async def startup_event():
    """Initialize FDO Tools on startup"""
    global fdo_tools_class, fdo_tools_manager

    logger.info("🚀 Starting AtomForge API Server v2.0 (daemon-only)")

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

        # Start daemon (mandatory; no fallback)
        daemon_exe = fdo_tools_manager.get_daemon_exe_path()
        if not daemon_exe:
            raise RuntimeError("fdo_daemon.exe not found in selected release or backend drop")

        bind = os.getenv("FDO_DAEMON_BIND", "127.0.0.1")
        port_env = os.getenv("FDO_DAEMON_PORT", "0")
        port = int(port_env) if port_env.isdigit() else 0
        log_path = os.getenv("FDO_DAEMON_LOG")

        # Start manager and client
        global daemon_manager, daemon_client
        daemon_manager = FdoDaemonManager(
            exe_path=daemon_exe,
            bind_host=bind,
            port=(port or None),
            log_path=log_path,
        )
        daemon_manager.start()

        token = os.getenv("FDO_DAEMON_TOKEN")
        daemon_client = FdoDaemonClient(base_url=daemon_manager.base_url, token=token)

        # Confirm health
        health = daemon_client.health()
        logger.info(f"FDO Daemon health: {health}")

    except Exception as e:
        logger.error(f"Failed to initialize FDO Tools: {e}")
        raise


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health = daemon_client.health()
        release_info = fdo_tools_manager.get_release_info()

        return {
            "status": "healthy" if health else "degraded",
            "service": "atomforge-fdo-api",
            "version": "2.0.0",
            "features": [
                "compilation",
                "decompilation"
            ],
            "daemon": {
                "base_url": daemon_manager.base_url,
                "bind": daemon_manager.bind_host,
                "port": daemon_manager.port,
                "health": health,
            },
            "release": {
                "path": release_info.get("path"),
                "bin_dir": release_info.get("bin_dir"),
            },
            "execution_mode": "daemon"
        }

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
            # Pass-through daemon error details with normalized error payload
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
            source_code = daemon_client.decompile_binary(binary_data)
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