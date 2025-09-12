# FDO Compiler - Linux with Wine for Ada32.dll support
FROM ubuntu:22.04

# Install Wine and dependencies for running Windows DLL
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

# Set working directory
WORKDIR /ada32_toolkit

# Copy project files
COPY . .

# Make scripts executable
RUN chmod +x fdo_compile.py

# Default command - run bash for interactive use
CMD ["bash"]
