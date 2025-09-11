# Linux with Wine for 32-bit Windows DLL support
FROM ubuntu:22.04

# Install Wine and dependencies for running Windows DLL
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    wine \
    wine32 \
    python3 python3-pip \
    wget \
    xvfb \
    file \
    gcc-mingw-w64-i686 \
    && rm -rf /var/lib/apt/lists/*

# Configure Wine for 32-bit architecture
ENV WINEPREFIX=/wine
ENV WINEARCH=win32
ENV DISPLAY=:99
RUN Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 & \
    sleep 2 && \
    wine wineboot --init && \
    pkill Xvfb

# Set working directory
WORKDIR /ada32_toolkit

# Copy project files
COPY . .

# Verify Ada32.dll is present and examine it
RUN ls -la Ada32.dll || echo "WARNING: Ada32.dll not found"
RUN file Ada32.dll || echo "Cannot determine file type"

# Compile the Ada32 bridge for Windows
RUN i686-w64-mingw32-gcc -o ada32_bridge.exe ada32_bridge.c -lkernel32

# Test Python version
RUN python3 -c "import sys; print('Python version:', sys.version); print('Platform:', sys.platform)"

# Create a Wine wrapper for running Ada32.dll through Python
RUN echo '#!/bin/bash\nexport DISPLAY=:99\nXvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &\nexec python3 "$@"' > /usr/local/bin/wine-python && \
    chmod +x /usr/local/bin/wine-python

# Default command  
CMD ["wine-python", "ada32_runner.py"]