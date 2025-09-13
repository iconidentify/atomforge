# AtomForge - All-in-One Docker Container
# Wine + Ada32.dll + Python API server + web interface
FROM ubuntu:22.04

# Install system dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        wine \
        wine32 \
        python3 \
        python3-pip \
        file \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Configure Wine environment
ENV WINEPREFIX=/wine \
    WINEARCH=win32 \
    PYTHONPATH=/atomforge \
    PORT=8000 \
    HOST=0.0.0.0

# Initialize Wine (headless)
RUN wine wineboot --init && wineserver -w

# Set working directory
WORKDIR /atomforge

# Copy requirements first for better layer caching
COPY api/requirements.txt ./api/
RUN pip3 install -r api/requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the API server
CMD ["python3", "-m", "api.src.api_server"]