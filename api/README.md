# AtomForge HTTP API

HTTP REST API service for compiling FDO source code using authentic Ada32.dll.

## Features

- **Simple REST API** - Clean, elegant interface
- **Binary Response** - Preserves compiled FDO binary format
- **Proper Error Handling** - Detailed error responses for failures
- **Health Monitoring** - Built-in health check endpoint
- **Docker Ready** - Containerized with Wine environment
- **Development Mode** - Auto-reload for development

## API Endpoints

### `POST /compile`
Compile FDO source code to binary format.

**Request:**
```json
{
  "source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n  man_end_object <>\nuni_end_stream <>"
}
```

**Success Response (200):**
- Content-Type: `application/octet-stream`
- Headers: `X-Compile-Success: true`, `X-Output-Size: {bytes}`
- Body: Binary FDO data

**Error Response (400/500):**
```json
{
  "success": false,
  "error": "Ada32 compilation failed - invalid FDO syntax",
  "details": {
    "input_size": 123,
    "compilation_attempted": true
  }
}
```

### `GET /health`
Health check endpoint.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "fdo-compiler-api",
  "version": "1.0.0"
}
```

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start the API service
cd api
docker-compose up --build

# API will be available at:
# http://localhost:8000 (Swagger docs)
# http://localhost:8000/health (Health check)
```

### Local Development

```bash
# Install dependencies
cd api
pip install -r requirements.txt

# Start development server
python src/api_server.py

# Server will start with auto-reload at http://localhost:8000
```

## Usage Examples

### Using curl

```bash
# Compile FDO source
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source": "uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n  man_end_object <>\nuni_end_stream <>"}' \
  --output compiled.fdo

# Check health
curl http://localhost:8000/health
```

### Using Python requests

```python
import requests

# Compile FDO
response = requests.post('http://localhost:8000/compile', json={
    'source': '''uni_start_stream <00x>
  man_start_object <independent, "Test">
  man_end_object <>
uni_end_stream <>'''
})

if response.status_code == 200:
    # Save binary output
    with open('output.fdo', 'wb') as f:
        f.write(response.content)
    print(f"Compiled successfully: {response.headers['X-Output-Size']} bytes")
else:
    # Handle error
    error = response.json()
    print(f"Compilation failed: {error['error']}")
```

## Architecture

The API service is built with:

- **FastAPI** - Modern Python web framework
- **Shared Compiler Module** - Reuses core compilation logic
- **Docker + Wine** - Same environment as CLI compiler
- **Elegant Error Handling** - Proper HTTP status codes and detailed errors
- **Binary Response Support** - Preserves FDO binary format

The shared `fdo_compiler.py` module provides code reuse between the CLI tool and HTTP API, ensuring consistency and maintainability.