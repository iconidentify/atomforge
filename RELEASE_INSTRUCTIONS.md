# 🚀 FDO API Release Instructions

## For End Users

### Quick Start (3 Commands)

```bash
# 1. Download and run the API
docker run -p 8000:8000 ghcr.io/iconidentify/ada32-toolkit:latest

# 2. Open API documentation in browser
open http://localhost:8000

# 3. Compile your first FDO file
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{"source": "uni_start_stream <00x>\n  man_start_object <independent, \"Hello World\">\n  man_end_object <>\nman_end_stream <>"}' \
  --output hello.fdo
```

### Alternative: Docker Compose (Even Easier)

```bash
# Download the docker-compose file
curl -O https://raw.githubusercontent.com/iconidentify/ada32-toolkit/main/docker-compose.api.yml

# Start the API
docker-compose -f docker-compose.api.yml up -d

# API is now running at http://localhost:8000
```

## API Usage Examples

### Compile FDO Text
```bash
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{
    "source": "uni_start_stream <00x>\n  man_start_object <independent, \"My Room\">\n    man_add_button <\"OK\", 100, 100, 50, 30>\n  man_end_object <>\nman_end_stream <>"
  }' \
  --output myroom.fdo
```

### Check API Health
```bash
curl http://localhost:8000/health
# Returns: {"status": "healthy", "version": "v1.x.x"}
```

### View API Documentation
- **Swagger UI**: http://localhost:8000/
- **Interactive Testing**: Click "Try it out" on any endpoint
- **Download OpenAPI Spec**: http://localhost:8000/openapi.json

## What You Get

✅ **Complete FDO Compilation Environment**
- Original Ada32.dll from AOL (1997)
- Wine emulation for cross-platform compatibility
- All dependencies pre-configured

✅ **Professional REST API**
- Clean JSON request/response format
- Comprehensive error handling
- Binary file downloads

✅ **User-Friendly**
- Single Docker command to start
- Interactive web interface
- Clear documentation and examples

## System Requirements

- **Docker Engine** (20.10+)
- **RAM**: 1GB minimum, 2GB recommended
- **Disk**: ~500MB for Docker image
- **Network**: Internet connection for initial download

## Troubleshooting

### API Won't Start
```bash
# Check Docker is running
docker ps

# Check container logs
docker logs fdo-api

# Restart with verbose logging
docker run -p 8000:8000 -e LOG_LEVEL=DEBUG ghcr.io/iconidentify/ada32-toolkit:latest
```

### Compilation Errors
- Make sure your FDO text doesn't contain unescaped `&` characters
- Check that your FDO syntax is valid
- Verify the API is healthy: `curl http://localhost:8000/health`

### Port 8000 Already in Use
```bash
# Use a different port
docker run -p 8080:8000 ghcr.io/iconidentify/ada32-toolkit:latest
# API will be available at http://localhost:8080
```

## Advanced Usage

### Custom Docker Configuration
```yaml
version: '3.8'
services:
  fdo-api:
    image: ghcr.io/iconidentify/ada32-toolkit:latest
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - MAX_WORKERS=4
    volumes:
      - ./output:/app/output  # Mount output directory
    restart: unless-stopped
```

### Integration with Other Tools
```bash
# Compile and immediately process the result
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d @myinput.json \
  -o compiled.fdo \
  && ./process_fdo compiled.fdo
```

## Support

- **GitHub Issues**: https://github.com/iconidentify/ada32-toolkit/issues
- **API Documentation**: http://localhost:8000/ (when running)
- **Health Check**: http://localhost:8000/health

## Version History

See [GitHub Releases](https://github.com/iconidentify/ada32-toolkit/releases) for changelog and upgrade instructions.
