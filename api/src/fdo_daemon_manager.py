#!/usr/bin/env python3
"""
FDO Daemon Process Manager
Starts and supervises the Windows daemon under Wine inside the container.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from typing import Optional

import httpx
import psutil


def _pick_free_port(bind: str = "127.0.0.1") -> int:
    s = socket.socket()
    s.bind((bind, 0))
    try:
        return s.getsockname()[1]
    finally:
        s.close()


class FdoDaemonManager:
    def __init__(
        self,
        exe_path: str,
        bind_host: str = "127.0.0.1",
        port: Optional[int] = None,
        log_path: Optional[str] = None,
        startup_timeout_seconds: float = 12.0,
    ) -> None:
        self.exe_path = exe_path
        self.bind_host = bind_host
        self.port = port or _pick_free_port(bind_host)
        self.log_path = log_path
        self.startup_timeout_seconds = startup_timeout_seconds
        self._proc: Optional[subprocess.Popen] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.bind_host}:{self.port}"

    def start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return  # already running

        wine = os.environ.get("WINE", "wine")
        cmd = [wine, self.exe_path, "--host", self.bind_host, "--port", str(self.port)]

        stdout = subprocess.DEVNULL
        if self.log_path:
            # Open in append-binary mode so logs persist across restarts
            stdout = open(self.log_path, "ab")

        # Ensure daemon runs with its DLLs present by setting cwd to exe directory
        cwd = os.path.dirname(self.exe_path) or None
        self._proc = subprocess.Popen(cmd, stdout=stdout, stderr=stdout, cwd=cwd)

        # Wait until health endpoint responds
        deadline = time.time() + self.startup_timeout_seconds
        while time.time() < deadline:
            try:
                r = httpx.get(f"{self.base_url}/health", timeout=0.5)
                if r.status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("FDO daemon failed to become healthy in time")

    def stop(self) -> None:
        if self._proc is None:
            return

        try:
            proc = psutil.Process(self._proc.pid)
            for child in proc.children(recursive=True):
                try:
                    child.terminate()
                except Exception:
                    pass
            try:
                proc.terminate()
                _, _ = psutil.wait_procs([proc], timeout=3)
            except Exception:
                pass

            if proc.is_running():
                try:
                    proc.kill()
                except Exception:
                    pass
        finally:
            self._proc = None


