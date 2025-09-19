#!/usr/bin/env python3
"""
FDO Compiler HTTP API Service
Elegant REST API for FDO compilation using Ada32.dll

Endpoints:
- POST /compile - Compile FDO source to binary
- GET /health - Health check
"""

import os
import sys
import re
import glob
from typing import Dict, Any, List
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
import logging
from starlette.concurrency import run_in_threadpool

logging.basicConfig(level=logging.ERROR, filename='/var/log/atomforge.log', format='%(asctime)s - %(levelname)s - %(message)s')

# Add our compiler modules to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdo_compiler import FDOCompiler, CompileResult
from fdo_decompiler import FDODecompiler, DecompileResult
from p3_extractor import P3Extractor

# Import ASCII support modules
try:
    from ascii_atom_registry import get_registry, get_ascii_atoms
    ASCII_SUPPORT_AVAILABLE = True
except ImportError:
    ASCII_SUPPORT_AVAILABLE = False

# Import P3 extractor
try:
    from p3_extractor import get_extractor
    P3_SUPPORT_AVAILABLE = True
except ImportError:
    P3_SUPPORT_AVAILABLE = False


class CompileRequest(BaseModel):
    """Request model for FDO compilation"""
    source: str = Field(..., description="FDO source code to compile", min_length=1)


class DecompileRequest(BaseModel):
    """Request model for FDO decompilation"""
    binary_data: str = Field(..., description="Base64-encoded FDO binary data to decompile", min_length=1)

class ExtractRequest(BaseModel):
    """Request model for extracting FDO from P3 hex payloads"""
    hex_data: str = Field(..., description="Hex-encoded P3 packet data", min_length=1)
    strict_crc: bool = Field(default=False, description="Enable strict CRC validation")


class ExtractFDORequest(BaseModel):
    """Request model for P3 packet FDO extraction"""
    hex_data: str = Field(..., description="Hex string containing P3 packets", min_length=1)


class CompileErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str = Field(..., description="Error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class ExampleResponse(BaseModel):
    """FDO example model"""
    id: str = Field(..., description="Example identifier")
    name: str = Field(..., description="Human-readable name")
    source: str = Field(..., description="FDO source code")
    description: str = Field(default="", description="Optional description")


app = FastAPI(
    title="AtomForge FDO API",
    description="HTTP API for compiling and decompiling FDO files using authentic Ada32.dll",
    version="2.0.0",
    docs_url="/api",  # Swagger UI at /api
    redoc_url="/docs"
)

# Mount static files for web interface
static_paths = [
    "/atomforge/api/static",  # Inside container
    "../static", 
    "static"
]

for static_path in static_paths:
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")
        print(f"📁 Mounted static files from: {os.path.abspath(static_path)}")
        break
else:
    print("⚠️  Static files directory not found!")

# Global compiler and decompiler instances
compiler = FDOCompiler()
decompiler = FDODecompiler()


@app.get("/")
async def web_interface():
    """Serve the web interface"""
    static_paths = [
        "/atomforge/api/static/index.html",  # Inside container
        "../static/index.html",
        "static/index.html"
    ]
    
    for path in static_paths:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
    
    # Fallback if static files not found
    return JSONResponse({
        "message": "FDO Compiler Web Interface",
        "api_docs": "/api",
        "health": "/health",
        "compile_endpoint": "/compile"
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "atomforge-fdo-api",
        "version": "2.0.0",
        "features": ["compilation", "decompilation", "p3_extraction" if P3_SUPPORT_AVAILABLE else None]
    }


def load_golden_examples() -> List[ExampleResponse]:
    """Load FDO examples from golden test files"""
    examples = []

    # Look for golden test files in new location
    golden_paths = [
        "/atomforge/bin/golden_tests_immutable/*.txt",  # Inside container
        "bin/fdo_compiler_decompiler/golden_tests_immutable/*.txt",  # Development
        "../bin/fdo_compiler_decompiler/golden_tests_immutable/*.txt"
    ]
    
    for pattern in golden_paths:
        files = glob.glob(pattern)
        if files:
            break
    
    if not files:
        # Fallback examples if no golden tests found
        return [
            ExampleResponse(
                id="basic",
                name="Basic Example",
                source="""uni_start_stream <00x>
  man_start_object <independent, "Basic Example">
    mat_object_id <basic-001>
    mat_orientation <vcf>
    mat_position <center_center>
  man_end_object <>
uni_end_stream <>""",
                description="Simple FDO object example"
            )
        ]
    
    # Process golden test files
    for file_path in sorted(files)[:12]:  # Limit to first 12 examples
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove GID header and comment lines if present
            content = re.sub(r'^<+.*?GID:.*?>+.*?\n', '', content, flags=re.MULTILINE)
            content = re.sub(r'^>>>>.*?\n', '', content, flags=re.MULTILINE)  # Remove comment lines
            content = content.strip()
            
            if content and 'uni_start_stream' in content:
                # Extract file identifier (e.g., "32-105" from "32-105.txt")
                file_id = os.path.basename(file_path).replace('.txt', '')
                
                # Create a readable name from the first object description if available
                name_match = re.search(r'man_start_object\s*<[^,]*,\s*"([^"]+)"', content)
                display_name = name_match.group(1) if name_match else f"Example {file_id}"
                
                examples.append(ExampleResponse(
                    id=file_id,
                    name=display_name,
                    source=content,
                    description=f"Golden test example from {file_id}.txt"
                ))
        except Exception as e:
            print(f"Error loading golden test {file_path}: {e}")
            continue
    
    return examples


@app.get("/examples", response_model=List[ExampleResponse])
async def get_examples():
    """Get available FDO examples from golden tests"""
    try:
        examples = load_golden_examples()
        return examples
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load examples: {str(e)}"
        )


@app.get("/ascii-atoms")
async def get_ascii_atoms():
    """Get list of atoms that support ASCII text input"""
    if not ASCII_SUPPORT_AVAILABLE:
        return {
            "ascii_support": False,
            "atoms": [],
            "message": "ASCII atom support not available"
        }

    try:
        ascii_atoms = get_ascii_atoms()
        registry = get_registry()

        # Build detailed atom information
        atom_details = []
        for atom_name in ascii_atoms:
            atom_def = registry.get_atom(atom_name)
            if atom_def:
                atom_info = {
                    "name": atom_name,
                    "description": atom_def.description,
                    "parameters": [
                        {
                            "index": param.index,
                            "name": param.name,
                            "type": param.type,
                            "max_length": param.max_length,
                            "encoding": param.encoding
                        }
                        for param in atom_def.parameters
                    ]
                }
                atom_details.append(atom_info)

        return {
            "ascii_support": True,
            "atoms": atom_details,
            "count": len(atom_details)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load ASCII atoms: {str(e)}"
        )


@app.post("/compile")
async def compile_fdo(request: CompileRequest):
    """
    Compile FDO source code to binary format
    
    Returns:
        - Success: Binary FDO data (application/octet-stream)
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
        
        # Attempt compilation
        result: CompileResult = await run_in_threadpool(compiler.compile_from_string, source)
        
        if result.success:
            # Return binary data with appropriate headers
            return Response(
                content=result.output_data,
                media_type="application/octet-stream",
                headers={
                    "Content-Length": str(result.output_size),
                    "X-Compile-Success": "true",
                    "X-Output-Size": str(result.output_size)
                }
            )
        else:
            # Return JSON error response
            logging.error(f"Compile failed: {result.error_message}\nStdout: {result.stdout}\nStderr: {result.stderr}")
            status_code = 400  # Bad Request for compilation errors
            if "Docker" in result.error_message:
                status_code = 500  # Internal Server Error for infrastructure issues
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    "success": False,
                    "error": result.error_message,
                    "details": {
                        "input_size": len(source),
                        "compilation_attempted": True
                    }
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected compile error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error",
                "details": {"exception": str(e)}
            }
        )


@app.post("/decompile")
async def decompile_fdo(request: DecompileRequest):
    """
    Decompile FDO binary data to source code

    Returns:
        - Success: JSON response with source code
        - Error: JSON error response
    """
    import base64

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
                    "error": "Empty binary data provided",
                    "details": {"field": "binary_data"}
                }
            )

        # Attempt decompilation
        result: DecompileResult = await run_in_threadpool(decompiler.decompile_from_bytes, binary_data)

        if result.success:
            # Return JSON response with source code
            return {
                "success": True,
                "source_code": result.source_code,
                "output_size": result.output_size,
                "input_size": len(binary_data)
            }
        else:
            # Return JSON error response
            logging.error(f"Decompile failed: {result.error_message}\nStdout: {result.stdout}\nStderr: {result.stderr}")
            status_code = 400  # Bad Request for decompilation errors
            if "Docker" in result.error_message:
                status_code = 500  # Internal Server Error for infrastructure issues

            raise HTTPException(
                status_code=status_code,
                detail={
                    "success": False,
                    "error": result.error_message,
                    "details": {
                        "input_size": len(binary_data),
                        "decompilation_attempted": True
                    }
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected decompile error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error",
                "details": {"exception": str(e)}
            }
        )


@app.post("/extract-fdo")
async def extract_fdo_from_p3(request: ExtractFDORequest):
    """
    Extract FDO data from P3 packet streams

    Takes hex string containing P3 packets and extracts clean FDO data
    for decompilation purposes.

    Returns:
        - Success: JSON response with extracted FDO hex data
        - Error: JSON error response
    """
    if not P3_SUPPORT_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail={
                "success": False,
                "error": "P3 extraction not available",
                "details": {"feature": "p3_support", "available": False}
            }
        )

    try:
        # Validate input
        hex_data = request.hex_data.strip()
        if not hex_data:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "Empty hex data provided",
                    "details": {"field": "hex_data"}
                }
            )

        # Extract FDO from P3 packets
        extractor = get_extractor()
        result = await run_in_threadpool(extractor.extract_fdo_from_hex, hex_data)

        if result['success']:
            return {
                "success": True,
                "fdo_hex": result['fdo_hex'],
                "frames_found": result['frames_found'],
                "total_fdo_bytes": result['total_fdo_bytes'],
                "input_size": len(hex_data)
            }
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": result['error'],
                    "details": {
                        "frames_found": result['frames_found'],
                        "input_size": len(hex_data),
                        "extraction_attempted": True
                    }
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected P3 extraction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error during P3 extraction",
                "details": {"exception": str(e)}
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler to ensure consistent JSON error responses"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting FDO Compiler API")
    print(f"   Server: http://{host}:{port}")
    print(f"   Docs:   http://{host}:{port}/")
    print(f"   Health: http://{host}:{port}/health")
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=True if os.getenv("ENV") == "development" else False,
        log_level="info"
    )