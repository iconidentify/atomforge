#!/usr/bin/env python3
"""
FDO Daemon Process Manager
Starts and supervises the Windows daemon under Wine inside the container.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


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
        startup_timeout_seconds: float = 30.0,  # Increased for Wine + Ada32 initialization
    ) -> None:
        self.exe_path = exe_path
        self.bind_host = bind_host
        self.port = port or _pick_free_port(bind_host)
        self.startup_timeout_seconds = startup_timeout_seconds
        self._proc: Optional[subprocess.Popen] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.bind_host}:{self.port}"

    def health_check(self) -> bool:
        """
        Perform a health check on the daemon.
        Returns True if daemon is healthy, False otherwise.
        """
        try:
            r = httpx.get(f"{self.base_url}/health", timeout=1.0)
            return r.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed for {self.base_url}: {e}")
            return False

    def start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return  # already running

        wine = os.environ.get("WINE", "wine")
        cmd = [wine, self.exe_path, "--host", self.bind_host, "--port", str(self.port)]

        # Ensure daemon runs with its DLLs present by setting cwd to exe directory
        cwd = os.path.dirname(self.exe_path) or None

        # Redirect stdout/stderr to log files for debugging
        stdout_log = open("/tmp/fdo_daemon_stdout.log", "w")
        stderr_log = open("/tmp/fdo_daemon_stderr.log", "w")

        logger.info(f"Starting daemon: {' '.join(cmd)}")
        logger.info(f"Working directory: {cwd}")
        logger.info(f"Logs: /tmp/fdo_daemon_stdout.log and /tmp/fdo_daemon_stderr.log")

        # Start process with redirected output
        self._proc = subprocess.Popen(cmd, cwd=cwd, stdout=stdout_log, stderr=stderr_log)

        # Wait until health endpoint responds
        deadline = time.time() + self.startup_timeout_seconds
        while time.time() < deadline:
            try:
                r = httpx.get(f"{self.base_url}/health", timeout=0.5)
                if r.status_code == 200:
                    logger.info(f"Daemon healthy on {self.base_url}")
                    return
            except Exception as e:
                logger.debug(f"Health check failed: {e}")
            time.sleep(0.2)

        # Log failure details
        logger.error(f"Daemon failed to start after {self.startup_timeout_seconds}s")
        logger.error(f"Process status: {'running' if self._proc.poll() is None else 'terminated'}")
        if self._proc.poll() is not None:
            logger.error(f"Process exit code: {self._proc.poll()}")

        raise RuntimeError("FDO daemon failed to become healthy in time")

    def stop(self) -> None:
        if self._proc is None:
            return

        try:
            # Simple process termination
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                self._proc.kill()
                self._proc.wait()
        except Exception:
            pass  # Ignore errors during shutdown
        finally:
            self._proc = None


