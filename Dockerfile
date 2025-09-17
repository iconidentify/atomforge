# ================================
# AtomForge - Minimal Wine FDO Compiler
# Lightweight Docker environment for FDO compilation & decompilation
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
    wine wineboot --init 2>/dev/null && \
    wineserver -w && \
    rm -rf /tmp/.wine-* 2>/dev/null || true

WORKDIR /atomforge

# Install Python dependencies
COPY api/requirements.txt ./api/
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy essential project files only
COPY api/ ./api/
COPY bin/fdo_compiler_decompiler/ ./bin/
RUN cp -r ./bin/golden_tests_immutable ./bin/ 2>/dev/null || echo "Golden tests already in correct location"

# Install mfc42.dll for Wine MFC support (required for FDO tools)
RUN if [ -f ./bin/mfc42.dll ]; then \
        echo "Installing mfc42.dll for Wine MFC support..." && \
        cp ./bin/mfc42.dll $WINEPREFIX/drive_c/windows/system32/ && \
        cd $WINEPREFIX/drive_c/windows/system32 && \
        wine regsvr32 /s mfc42.dll && \
        echo "mfc42.dll registered successfully"; \
    else \
        echo "WARNING: mfc42.dll not found - FDO compilation may fail"; \
    fi

# Expose web interface port
EXPOSE 8000

# Health check for production readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the web service
CMD ["python3", "-m", "api.src.api_server"]