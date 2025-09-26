#!/usr/bin/env python3
"""
FDO Tools Release Manager
Handles discovery and loading of FDO Tools releases
"""

import os
import sys
import re
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FdoToolsManager:
    """Manages FDO Tools release discovery and loading"""

    def __init__(self, releases_dir: Optional[str] = None):
        """
        Initialize FDO Tools manager

        Args:
            releases_dir: Directory containing FDO Tools releases (auto-detected if None)
        """
        self.releases_dir = releases_dir or self._find_releases_dir()
        self.selected_release = None
        self.fdo_tools = None

    def _find_releases_dir(self) -> str:
        """Find releases directory using standard search paths"""
        search_paths = [
            os.environ.get("FDO_RELEASES_DIR"),
            "/atomforge/releases",  # Docker environment
            "./releases",
            "../releases",
            os.path.join(os.path.dirname(__file__), "..", "..", "releases")
        ]

        for path in search_paths:
            if path and os.path.isdir(path):
                logger.info(f"Found releases directory: {path}")
                return path

        raise RuntimeError("FDO Tools releases directory not found. "
                          "Please set FDO_RELEASES_DIR environment variable or ensure releases/ exists.")

    def discover_releases(self) -> Dict[str, str]:
        """
        Discover available FDO Tools releases

        Returns:
            Dictionary mapping version -> release_path
        """
        releases = {}

        if not os.path.exists(self.releases_dir):
            logger.warning(f"Releases directory does not exist: {self.releases_dir}")
            return releases

        for item in os.listdir(self.releases_dir):
            item_path = os.path.join(self.releases_dir, item)

            # Look for fdo_tools_vX.X.X directories
            if os.path.isdir(item_path) and item.startswith("fdo_tools_v"):
                version_match = re.match(r"fdo_tools_v(\d+\.\d+\.\d+)", item)
                if version_match:
                    version = version_match.group(1)

                    # Verify release has required structure
                    if self._validate_release(item_path):
                        releases[version] = item_path
                        logger.debug(f"Found valid release: {version} at {item_path}")

            # Also support new atomforge-backend drop (single backend folder)
            # Treat it as version "backend" to make selection deterministic if present.
            if os.path.isdir(item_path) and item == "atomforge-backend":
                # Minimal validation: daemon + Ada32.dll + compiler/decompiler. Accept ADA.BIN or Ada.bin (case-insensitive)
                required_present = all(os.path.exists(os.path.join(item_path, f)) for f in [
                    "fdo_daemon.exe",
                    "fdo_compiler.exe",
                    "fdo_decompiler.exe",
                    "Ada32.dll",
                ])
                ada_bin_present = any(os.path.exists(os.path.join(item_path, name)) for name in [
                    "Ada.bin", "ADA.BIN", "ada.bin"
                ])
                if required_present and ada_bin_present:
                    # Register a pseudo-version that sorts after numeric versions
                    releases["9999.9999.9999"] = item_path
                    logger.info(f"Found atomforge-backend at {item_path} (registered as latest)")

        logger.info(f"Discovered {len(releases)} FDO Tools releases")
        return releases

    def _validate_release(self, release_path: str) -> bool:
        """Validate that release has required files"""
        required_files = [
            "bin/fdo_compiler.exe",
            "bin/fdo_decompiler.exe",
            "bin/Ada32.dll",
            "bin/Ada.bin",
            "python/fdo_tools/__init__.py"
        ]

        for required_file in required_files:
            if not os.path.exists(os.path.join(release_path, required_file)):
                logger.warning(f"Release {release_path} missing required file: {required_file}")
                return False

        return True

    def select_latest_release(self) -> Optional[str]:
        """
        Select the latest available release

        Returns:
            Path to selected release or None if no releases found
        """
        releases = self.discover_releases()

        if not releases:
            logger.error("No valid FDO Tools releases found")
            return None

        # Sort versions and select latest
        versions = list(releases.keys())
        versions.sort(key=lambda v: [int(x) for x in v.split('.')])
        latest_version = versions[-1]

        self.selected_release = releases[latest_version]
        logger.info(f"Selected FDO Tools release: v{latest_version} at {self.selected_release}")

        return self.selected_release

    def load_fdo_tools(self, release_path: Optional[str] = None) -> Any:
        """
        Load FDO Tools from specified or latest release

        Args:
            release_path: Specific release path (uses latest if None)

        Returns:
            FdoTools class from the selected release
        """
        if release_path is None:
            release_path = self.selected_release or self.select_latest_release()

        if not release_path:
            raise RuntimeError("No FDO Tools release available")

        # Add Python module to path
        python_module_path = os.path.join(release_path, "python")
        if python_module_path not in sys.path:
            sys.path.insert(0, python_module_path)
            logger.debug(f"Added to Python path: {python_module_path}")

        # Set environment variable for bin directory
        bin_dir = os.path.join(release_path, "bin")
        os.environ["FDO_TOOLS_BIN_DIR"] = bin_dir
        logger.debug(f"Set FDO_TOOLS_BIN_DIR: {bin_dir}")

        try:
            # Import and return FdoTools class
            from fdo_tools import FdoTools
            logger.info(f"Successfully loaded FDO Tools from {release_path}")
            return FdoTools

        except ImportError as e:
            raise RuntimeError(f"Failed to import FDO Tools from {release_path}: {e}")

    def get_release_info(self, release_path: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a release"""
        if release_path is None:
            release_path = self.selected_release

        if not release_path:
            return {}

        info = {
            "path": release_path,
            "bin_dir": os.path.join(release_path, "bin"),
            "python_dir": os.path.join(release_path, "python"),
            "valid": self._validate_release(release_path)
        }

        # Try to read version info
        version_file = os.path.join(release_path, "VERSION.txt")
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                info["version_info"] = f.read().strip()

        return info

    # --- New helpers for daemon-first integration ---
    def get_daemon_exe_path(self) -> Optional[str]:
        """Return path to fdo_daemon.exe for the selected release or backend drop."""
        # Case 1: curated release structure
        if self.selected_release and os.path.exists(os.path.join(self.selected_release, "bin", "fdo_daemon.exe")):
            return os.path.join(self.selected_release, "bin", "fdo_daemon.exe")

        # Case 2: atomforge-backend flat drop
        backend_path = os.path.join(self.releases_dir, "atomforge-backend", "fdo_daemon.exe")
        if os.path.exists(backend_path):
            return backend_path

        return None


# Global manager instance
_manager = None

def get_fdo_tools_manager() -> FdoToolsManager:
    """Get global FDO Tools manager instance"""
    global _manager
    if _manager is None:
        _manager = FdoToolsManager()
    return _manager

def get_fdo_tools() -> Any:
    """Get FDO Tools class from latest release"""
    manager = get_fdo_tools_manager()
    return manager.load_fdo_tools()