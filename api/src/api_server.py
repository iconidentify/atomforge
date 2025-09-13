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

# Add our compiler module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdo_compiler import FDOCompiler, CompileResult


class CompileRequest(BaseModel):
    """Request model for FDO compilation"""
    source: str = Field(..., description="FDO source code to compile", min_length=1)


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
    title="FDO Compiler API",
    description="HTTP API for compiling FDO source code using authentic Ada32.dll",
    version="1.0.0",
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

# Global compiler instance
compiler = FDOCompiler()


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
        "service": "fdo-compiler-api",
        "version": "1.0.0"
    }


def load_golden_examples() -> List[ExampleResponse]:
    """Load FDO examples from golden test files"""
    examples = []
    
    # Look for golden test files
    golden_paths = [
        "/atomforge/golden_tests_immutable/*.txt",  # Inside container
        "../golden_tests_immutable/*.txt",
        "../../golden_tests_immutable/*.txt"
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
            
            # Remove GID header if present
            content = re.sub(r'^<+.*?GID:.*?>+.*?\n', '', content, flags=re.MULTILINE)
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
        result: CompileResult = compiler.compile_from_string(source)
        
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
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal server error",
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