# FDO Compiler HTTP API
FROM ubuntu:22.04

# Install Wine, Python, and dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    wine \
    wine32 \
    python3 \
    python3-pip \
    xvfb \
    file \
    && rm -rf /var/lib/apt/lists/*

# Configure Wine for 32-bit architecture
ENV WINEPREFIX=/wine
ENV WINEARCH=win32
ENV DISPLAY=:99

# Initialize Wine
RUN Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 & \
    sleep 2 && \
    wine wineboot --init && \
    wineserver -w && \
    pkill Xvfb

# Install Python dependencies
COPY api/requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

# Set working directory
WORKDIR /ada32_toolkit

# Copy project files (will be mounted in development)
COPY . .

# Copy API source and static files  
COPY api/src/ /app/
COPY api/static/ /ada32_toolkit/api/static/
WORKDIR /app

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Start the API server
CMD ["python3", "api_server.py"]