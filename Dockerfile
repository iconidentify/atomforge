# ================================
# AtomForge Docker Image with Wine
# Web interface + FDO compilation capability
# ================================
FROM python:3.9-slim

# Install essential dependencies including minimal Wine
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        # Core Wine (minimal - no X11)
        wine \
        wine32 \
        # Essential tools
        curl \
        file \
        --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Remove Wine bloat we don't need
    rm -rf /usr/share/doc/wine* && \
    rm -rf /usr/share/man/man1/wine* && \
    find /usr -name "*.pdb" -delete 2>/dev/null || true

# Configure Wine for headless operation
ENV WINEPREFIX=/wine \
    WINEARCH=win32 \
    WINEDEBUG=-all \
    DISPLAY=:99 \
    PYTHONPATH=/atomforge \
    PORT=8000 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

# Initialize Wine prefix (headless)
RUN wine wineboot --init && \
    wineserver -w && \
    rm -rf /tmp/.wine-* 2>/dev/null || true

# Set working directory
WORKDIR /atomforge

# Copy and install Python dependencies
COPY api/requirements.txt ./api/
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the API server
CMD ["python3", "-m", "api.src.api_server"]