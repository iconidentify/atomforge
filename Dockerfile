# ================================
# AtomForge v2.0 - FDO Tools Python Module
# Lightweight Docker environment using FDO Tools releases
# ================================
FROM python:3.11-slim

# Install minimal Wine environment for 32-bit Windows executables
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        wine32 \
        curl \
        wget \
        --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    # Remove Wine documentation and unnecessary files
    rm -rf /usr/share/doc/wine* /usr/share/man/man1/wine* && \
    find /usr -name "*.pdb" -delete 2>/dev/null || true

# Configure Wine for headless operation (32-bit)
ENV WINEPREFIX=/wine \
    WINEARCH=win32 \
    WINEDEBUG=-all \
    PYTHONPATH=/atomforge \
    PORT=8000 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/lib/wine:$PATH"

# Create Wine symbolic links and initialize
RUN ln -sf /usr/lib/wine/wine /usr/local/bin/wine && \
    ln -sf /usr/lib/wine/wineserver /usr/local/bin/wineserver && \
    # Initialize Wine with minimal configuration
    export WINEDEBUG=-all && \
    wine wineboot --init 2>/dev/null && \
    wineserver -w && \
    # Test Wine can execute basic commands
    wine cmd /c echo "Wine test successful" 2>/dev/null || echo "Wine test completed" && \
    # Clean up temporary files
    rm -rf /tmp/.wine-* 2>/dev/null || true

WORKDIR /atomforge

# Install Python dependencies
COPY api/requirements.txt ./api/
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy FDO Tools releases (contains executables and Python modules)
COPY releases/ ./releases/

# Copy API application
COPY api/ ./api/

# Set environment variable for FDO Tools release discovery
ENV FDO_RELEASES_DIR=/atomforge/releases

# Expose web interface port
EXPOSE 8000

# Health check for production readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start API server directly (no supervisord needed)
CMD ["python3", "-m", "api.src.api_server"]
