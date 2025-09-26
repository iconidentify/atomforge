## AtomForge Backend - Binary Distribution Guide

This guide explains how to run the prebuilt Windows executables bundled in the AtomForge Backend binary zip, either on Windows or on Linux/macOS via Wine. It also documents the HTTP daemon and its API.

### What’s included

The zip contains the following files at the top level:

- fdo_compiler.exe
- fdo_decompiler.exe
- fdo_daemon.exe
- Ada32.dll
- SUPERSUB.DLL
- Ada.bin
- mfc42.dll
- mfc42u.dll
- msvcp60.dll
- msvcrt.dll
- docs/README-BINARY.md (this document)

All executables must be in the same directory as the DLLs above. Do not move DLLs to System32 or elsewhere; keep them next to the .exe files.

### System requirements

- Windows 10/11 (x64) or
- Linux/macOS with Wine (32‑bit prefix recommended)

On Linux (Debian/Ubuntu):

```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install -y wine wine32
```

Optional Wine tuning:

```bash
export WINEDEBUG=-all
export WINEARCH=win32
export WINEPREFIX=$HOME/.wine32
winecfg -v win7 || true
```

### Quick start: CLI tools

From the extracted directory:

- Compile FDO source (.txt) to binary (.bin):

```bash
# Windows
fdo_compiler.exe input.txt output.bin

# Linux/macOS (Wine)
wine fdo_compiler.exe input.txt output.bin
```

- Decompile binary (.bin) to human‑readable source (.txt):

```bash
# Windows
fdo_decompiler.exe input.bin output.txt

# Linux/macOS (Wine)
wine fdo_decompiler.exe input.bin output.txt
```

Exit codes: 0 = success, non‑zero = failure (see console output for an Ada32 or runtime message).

### Daemon: start and manage

Start the HTTP daemon (defaults to host 127.0.0.1 and port 8080):

```bash
# Windows
fdo_daemon.exe --port 8080

# Linux/macOS (Wine)
wine fdo_daemon.exe --port 8080
```

Useful options:

- --host HOST (default 127.0.0.1)
- --port PORT (default 8080)
- --threads N (default 4–8 depending on build)
- --quiet (suppress non‑error output)
- --verbose (extra diagnostics)

Stop with Ctrl+C. The daemon shuts down gracefully.

### HTTP API

Base URL: http://HOST:PORT

- POST /compile
  - Request: text/plain (FDO source text)
  - Response: application/octet-stream (compiled binary)
  - Example:

```bash
curl -s -X POST \
  -H "Content-Type: text/plain" \
  --data-binary @input.txt \
  http://127.0.0.1:8080/compile \
  -o output.bin
```

- POST /decompile
  - Request: application/octet-stream (binary data)
  - Response: text/plain (decompiled source)
  - Example:

```bash
curl -s -X POST \
  -H "Content-Type: application/octet-stream" \
  --data-binary @input.bin \
  http://127.0.0.1:8080/decompile \
  -o output.txt
```

- GET /health
  - Returns JSON with readiness, Ada32 loaded state, version, counters, and uptime.
  - Example:

```bash
curl -s http://127.0.0.1:8080/health | jq .
```

- GET /stats
  - Returns request counters and uptime.

### File layout recommendations

- Keep all shipped DLLs and Ada.bin next to the .exe files in the same folder.
- Keep your working input/output files outside this folder.
- For automation, use absolute paths when calling the executables.

### Troubleshooting

- “Failed to initialize FDO API (Ada32.dll loading failed)”
  - Ensure Ada32.dll and SUPERSUB.DLL are in the same folder as the .exe.
  - On Wine, confirm 32‑bit prefix (WINEARCH=win32) and try winecfg once.

- Wine prints fixme/err logs or crashes with an unhandled exception
  - Set `export WINEDEBUG=-all` to silence noise and retry.
  - Verify that all DLLs (mfc42.dll, mfc42u.dll, msvcp60.dll, msvcrt.dll) are present next to the .exe.

- Daemon starts but HTTP requests fail
  - Check firewall/antivirus rules.
  - On Wine, ensure the daemon terminal shows “Daemon is ready!” and test GET /health.

### Examples (Windows PowerShell)

```powershell
# Compile
./fdo_compiler.exe .\tests\golden\sample.txt .\out.bin

# Decompile
./fdo_decompiler.exe .\out.bin .\out.txt

# Start daemon
Start-Process -NoNewWindow -FilePath ./fdo_daemon.exe -ArgumentList "--port", "8080"

# Compile via HTTP
Invoke-WebRequest -Method POST -ContentType 'text/plain' -InFile .\tests\golden\sample.txt -Uri http://127.0.0.1:8080/compile -OutFile out.bin

# Decompile via HTTP
Invoke-WebRequest -Method POST -ContentType 'application/octet-stream' -InFile .\out.bin -Uri http://127.0.0.1:8080/decompile -OutFile out.txt
```

### Licensing and attribution

This package includes Microsoft Visual C++ 6.0 runtimes and components required by Ada32.dll. Ensure usage complies with your organization’s policy. See repository LICENSE for details.


