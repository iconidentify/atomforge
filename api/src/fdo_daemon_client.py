#!/usr/bin/env python3
"""
FDO Daemon HTTP Client
Speaks the vendor-documented HTTP interface:
  - POST /compile    (Content-Type: text/plain) -> application/octet-stream
  - POST /decompile  (Content-Type: application/octet-stream) -> text/plain
  - GET  /health     -> JSON
"""

from __future__ import annotations

import base64
import json
from typing import Optional, Dict, Any

import httpx


class FdoDaemonError(Exception):
    def __init__(self, status_code: int, content_type: str, text: str, body_bytes: bytes, json_obj: Optional[Dict[str, Any]] = None):
        super().__init__(f"Daemon HTTP {status_code}: {text[:256]}")
        self.status_code = status_code
        self.content_type = content_type
        self.text = text
        self.body_bytes = body_bytes
        self.json = json_obj


class FdoDaemonClient:
    """Thin synchronous client for the FDO daemon HTTP API."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.headers: Dict[str, str] = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def health(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            r = client.get(f"{self.base_url}/health", headers=self.headers)
            r.raise_for_status()
            return r.json()

    def compile_source(self, source_text: str) -> bytes:
        """Compile FDO source text to binary via daemon.

        Daemon expects raw text/plain body, returns application/octet-stream.
        """
        headers = {"Content-Type": "text/plain", **self.headers}
        data = source_text.encode("utf-8")
        with httpx.Client(timeout=self.timeout_seconds) as client:
            r = client.post(f"{self.base_url}/compile", headers=headers, content=data)
            if r.status_code >= 400:
                json_obj: Optional[Dict[str, Any]] = None
                try:
                    json_obj = r.json()
                except Exception:
                    # Fallback: attempt to parse text as JSON
                    try:
                        json_obj = json.loads(r.text)
                    except Exception:
                        json_obj = None
                raise FdoDaemonError(r.status_code, r.headers.get("Content-Type", ""), r.text, r.content, json_obj)
            return r.content

    def decompile_binary(self, binary_data: bytes) -> str:
        """Decompile binary to source via daemon.

        Daemon expects application/octet-stream body, returns text/plain.
        """
        headers = {"Content-Type": "application/octet-stream", **self.headers}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            r = client.post(f"{self.base_url}/decompile", headers=headers, content=binary_data)
            if r.status_code >= 400:
                json_obj: Optional[Dict[str, Any]] = None
                try:
                    json_obj = r.json()
                except Exception:
                    try:
                        json_obj = json.loads(r.text)
                    except Exception:
                        json_obj = None
                raise FdoDaemonError(r.status_code, r.headers.get("Content-Type", ""), r.text, r.content, json_obj)
            return r.text


