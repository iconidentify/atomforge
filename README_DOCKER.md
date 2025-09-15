# AtomForge - Optimized Docker Setup

## Quick Start

The optimized **AtomForge Full** image (2.4GB) includes everything needed for complete FDO compilation functionality.

### Start the Service

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or using Docker directly
docker run -d --name atomforge -p 8000:8000 atomforge-full:latest
```

### Access the Web Interface

- **Web Interface**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

### Test FDO Compilation

```bash
# Via curl
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source":"uni_start_stream <00x>\n  man_start_object <independent, \"Test\">\n    mat_object_id <test-123>\n  man_end_object <>\nuni_end_stream <>"}' \
  --output compiled.fdo

# Check if compilation succeeded
file compiled.fdo  # Should show binary data
```

### Stop the Service

```bash
docker-compose down
# or
docker stop atomforge && docker rm atomforge
```

## What's Included

- ✅ **FastAPI Web Interface** - Modern web UI for FDO compilation
- ✅ **Wine + Ada32.dll** - Complete Windows compilation environment
- ✅ **Health Checks** - Automatic monitoring and restart
- ✅ **Optimized Size** - 75% smaller than unoptimized builds
- ✅ **Production Ready** - Proper containerization and security

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker logs atomforge

# Check if port 8000 is available
lsof -i :8000
```

### Compilation Fails
```bash
# Check container is healthy
curl http://localhost:8000/health

# Test with a simple FDO example
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source":"uni_start_stream <00x>\n  man_start_object <independent, \"Test Object\">\n    mat_object_id <test-123>\n  man_end_object <>\nuni_end_stream <>"}'
```

### Performance Issues
- The 2.4GB image is optimized but still larger than the web-only version
- First compilation may take longer due to Wine initialization
- Subsequent compilations are much faster

## Development

To rebuild the optimized image:

```bash
# Build the full image with Wine
docker build -t atomforge-full .

# Test the build
docker run -d -p 8000:8000 --name test atomforge-full
```

## Architecture

The container includes:
- **Python 3.9** - FastAPI backend
- **Wine** - Windows compatibility layer
- **Ada32.dll** - FDO compilation engine
- **Compiled binaries** - Native atomforge.exe

All components are optimized for minimal size while maintaining full functionality.
