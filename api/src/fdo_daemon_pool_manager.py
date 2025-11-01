#!/usr/bin/env python3
"""
FDO Daemon Pool Manager

Manages a pool of fdo_daemon.exe instances for parallel request processing.
Each daemon runs in an isolated working directory with symlinked DLL files.
"""

import os
import time
import threading
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import shutil

from fdo_daemon_manager import FdoDaemonManager

logger = logging.getLogger(__name__)


@dataclass
class DaemonInstance:
    """Represents a single daemon in the pool."""
    id: str                           # e.g., "daemon_0"
    port: int                         # Assigned HTTP port
    working_dir: str                  # Isolated directory path
    bind_host: str                    # Bind address
    manager: Optional[FdoDaemonManager] = None  # Underlying daemon manager

    # Health and state
    state: str = "initializing"       # "healthy", "unhealthy", "crashed", "restarting"
    last_health_check: float = 0.0    # Timestamp of last health check
    circuit_breaker_open: bool = False  # Circuit breaker state

    # Metrics
    restart_count: int = 0            # Total restarts
    consecutive_failures: int = 0     # Current failure streak
    total_requests: int = 0           # Request counter
    failed_requests: int = 0          # Failed request counter

    # Request tracking for load balancing
    is_processing: bool = False       # True when actively processing a request
    request_started_at: Optional[float] = None  # Timestamp when request started


class FdoDaemonPoolManager:
    """
    Manages a pool of FDO daemon instances with load balancing and health monitoring.

    Features:
    - Round-robin load balancing
    - Automatic health monitoring
    - Circuit breaker per daemon
    - Automatic restart on failure
    - Isolated working directories with symlinked DLLs
    """

    def __init__(
        self,
        exe_path: str,
        pool_size: int = 5,
        base_port: int = 8080,
        bind_host: str = "127.0.0.1",
        restart_delay: float = 2.0,
        health_interval: float = 10.0,
        max_restart_attempts: int = 5,
        circuit_breaker_threshold: int = 3,
    ):
        """
        Initialize daemon pool manager.

        Args:
            exe_path: Path to fdo_daemon.exe
            pool_size: Number of daemon instances (1-20)
            base_port: Starting port number
            bind_host: Host address to bind daemons
            restart_delay: Delay before restarting crashed daemon (seconds)
            health_interval: Health check frequency (seconds)
            max_restart_attempts: Maximum restart attempts per daemon
            circuit_breaker_threshold: Failures before opening circuit breaker
        """
        # Validation
        if not os.path.exists(exe_path):
            raise ValueError(f"Daemon executable not found: {exe_path}")

        if not (1 <= pool_size <= 20):
            raise ValueError(f"Pool size must be 1-20, got: {pool_size}")

        if base_port + pool_size > 65535:
            raise ValueError(f"Port range exceeds maximum (base={base_port}, size={pool_size})")

        self.exe_path = exe_path
        self.bin_dir = os.path.dirname(exe_path)
        self.pool_size = pool_size
        self.base_port = base_port
        self.bind_host = bind_host
        self.restart_delay = restart_delay
        self.health_interval = health_interval
        self.max_restart_attempts = max_restart_attempts
        self.circuit_breaker_threshold = circuit_breaker_threshold

        # Pool state
        self.instances: List[DaemonInstance] = []
        self.current_index = 0  # Round-robin counter
        self.lock = threading.RLock()  # Thread-safe pool access

        # Health monitoring
        self.health_monitor_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()

        # Pool root directory
        self.pool_root = "/tmp/fdo_daemon_pool"

        logger.info(f"Initialized FdoDaemonPoolManager: size={pool_size}, ports={base_port}-{base_port + pool_size - 1}")

    def start(self) -> None:
        """
        Start all daemon instances and health monitoring thread.

        Raises:
            RuntimeError: If less than 50% of pool starts successfully
        """
        logger.info(f"Starting daemon pool with {self.pool_size} instances...")

        # Create pool root directory
        os.makedirs(self.pool_root, exist_ok=True)

        # Start each daemon instance
        successful_starts = 0
        for i in range(self.pool_size):
            try:
                instance = self._create_and_start_instance(i)
                self.instances.append(instance)
                successful_starts += 1
                logger.info(f"Started {instance.id} on port {instance.port}")
            except Exception as e:
                logger.error(f"Failed to start daemon_{i}: {e}")
                # Create placeholder instance in failed state
                instance = DaemonInstance(
                    id=f"daemon_{i}",
                    port=self.base_port + i,
                    working_dir="",
                    bind_host=self.bind_host,
                    state="crashed"
                )
                self.instances.append(instance)

        # Validate startup success rate
        success_rate = successful_starts / self.pool_size
        logger.info(f"Pool startup: {successful_starts}/{self.pool_size} instances started ({success_rate * 100:.0f}%)")

        if success_rate < 0.5:
            self.stop()  # Cleanup
            raise RuntimeError(f"Pool startup failed: only {successful_starts}/{self.pool_size} instances started")

        # Start health monitoring thread
        self.shutdown_event.clear()
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            name="PoolHealthMonitor",
            daemon=True
        )
        self.health_monitor_thread.start()
        logger.info("Health monitoring thread started")

    def stop(self) -> None:
        """Stop all daemons and health monitor."""
        logger.info("Stopping daemon pool...")

        # Signal health monitor to stop
        self.shutdown_event.set()
        if self.health_monitor_thread:
            self.health_monitor_thread.join(timeout=5.0)

        # Stop all daemon instances
        with self.lock:
            for instance in self.instances:
                if instance.manager:
                    try:
                        instance.manager.stop()
                        logger.info(f"Stopped {instance.id}")
                    except Exception as e:
                        logger.error(f"Error stopping {instance.id}: {e}")

        # Cleanup pool directories
        try:
            if os.path.exists(self.pool_root):
                shutil.rmtree(self.pool_root)
                logger.info(f"Cleaned up pool directory: {self.pool_root}")
        except Exception as e:
            logger.warning(f"Failed to cleanup pool directory: {e}")

        logger.info("Daemon pool stopped")

    def get_healthy_instance(self) -> Optional[DaemonInstance]:
        """
        Get next idle daemon, preferring daemons not currently processing requests.

        This ensures requests are distributed to idle daemons when available,
        preventing queue buildup on busy daemons.

        Returns:
            DaemonInstance if idle daemon available, None otherwise
        """
        with self.lock:
            if not self.instances:
                return None

            # First pass: Try to find an idle daemon (not currently processing)
            # Start from current_index for fair distribution
            for _ in range(len(self.instances)):
                instance = self.instances[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.instances)

                # Check if instance is healthy, idle, and circuit breaker is closed
                if (instance.state == "healthy" and
                    not instance.circuit_breaker_open and
                    not instance.is_processing):
                    # Mark as busy before returning
                    instance.is_processing = True
                    instance.request_started_at = time.time()
                    return instance

            # No idle daemon available
            return None

    def restart_instance(self, instance: DaemonInstance) -> bool:
        """
        Restart a specific daemon instance.

        Args:
            instance: DaemonInstance to restart

        Returns:
            True if restart successful, False otherwise
        """
        with self.lock:
            if instance.restart_count >= self.max_restart_attempts:
                logger.error(f"Max restart attempts reached for {instance.id}")
                return False

            instance.state = "restarting"
            instance.restart_count += 1

            logger.info(f"Restarting {instance.id} (attempt {instance.restart_count}/{self.max_restart_attempts})...")

            try:
                # Stop existing manager
                if instance.manager:
                    instance.manager.stop()

                # Wait before restart
                time.sleep(self.restart_delay)

                # Start new manager
                instance.manager = FdoDaemonManager(
                    exe_path=self.exe_path,
                    bind_host=instance.bind_host,
                    port=instance.port
                )
                instance.manager.start()

                instance.state = "healthy"
                instance.consecutive_failures = 0
                instance.circuit_breaker_open = False

                logger.info(f"Successfully restarted {instance.id}")
                return True

            except Exception as e:
                logger.error(f"Failed to restart {instance.id}: {e}")
                instance.state = "crashed"
                return False

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get comprehensive pool health and metrics.

        Returns:
            Dict with pool status, metrics, and per-instance details
        """
        with self.lock:
            instances_by_state = {}
            for instance in self.instances:
                state = instance.state
                instances_by_state[state] = instances_by_state.get(state, 0) + 1

            healthy_count = instances_by_state.get("healthy", 0)
            total_requests = sum(i.total_requests for i in self.instances)
            failed_requests = sum(i.failed_requests for i in self.instances)
            total_restarts = sum(i.restart_count for i in self.instances)

            # Load balancing metrics
            concurrent_requests = sum(1 for i in self.instances if i.is_processing)
            idle_daemons = sum(1 for i in self.instances
                             if i.state == "healthy" and not i.is_processing)

            return {
                "pool_size": self.pool_size,
                "instances_total": len(self.instances),
                "instances_healthy": healthy_count,
                "pool_health_percentage": (healthy_count / len(self.instances) * 100) if self.instances else 0,
                "total_requests": total_requests,
                "failed_requests": failed_requests,
                "daemon_restarts": total_restarts,
                "concurrent_requests": concurrent_requests,
                "idle_daemons": idle_daemons,
                "instances_by_state": instances_by_state,
                "instances": [
                    {
                        "id": instance.id,
                        "port": instance.port,
                        "state": instance.state,
                        "restart_count": instance.restart_count,
                        "consecutive_failures": instance.consecutive_failures,
                        "total_requests": instance.total_requests,
                        "failed_requests": instance.failed_requests,
                        "circuit_breaker_open": instance.circuit_breaker_open,
                        "last_health_check": instance.last_health_check,
                        "is_processing": instance.is_processing
                    }
                    for instance in self.instances
                ]
            }

    def reset_circuit_breakers(self) -> int:
        """
        Reset all circuit breakers.

        Returns:
            Number of circuit breakers reset
        """
        count = 0
        with self.lock:
            for instance in self.instances:
                if instance.circuit_breaker_open:
                    instance.circuit_breaker_open = False
                    instance.consecutive_failures = 0
                    instance.state = "healthy"
                    count += 1
                    logger.info(f"Reset circuit breaker for {instance.id}")

        logger.info(f"Reset {count} circuit breakers")
        return count

    # Private methods

    def _create_and_start_instance(self, instance_id: int) -> DaemonInstance:
        """Create and start a single daemon instance."""
        port = self.base_port + instance_id
        working_dir = self._provision_daemon_directory(instance_id)

        instance = DaemonInstance(
            id=f"daemon_{instance_id}",
            port=port,
            working_dir=working_dir,
            bind_host=self.bind_host
        )

        # Create and start daemon manager
        manager = FdoDaemonManager(
            exe_path=self.exe_path,
            bind_host=self.bind_host,
            port=port
        )
        manager.start()

        instance.manager = manager
        instance.state = "healthy"
        instance.last_health_check = time.time()

        return instance

    def _provision_daemon_directory(self, instance_id: int) -> str:
        """
        Create isolated working directory with symlinked files.

        Args:
            instance_id: Instance number

        Returns:
            Path to provisioned directory
        """
        daemon_dir = os.path.join(self.pool_root, f"daemon_{instance_id}")
        os.makedirs(daemon_dir, exist_ok=True)

        # Files to symlink
        required_files = [
            "fdo_daemon.exe",
            "fdo_compiler.exe",
            "fdo_decompiler.exe",
            "Ada32.dll",
            "ADA.BIN",
            "mfc42.dll",
            "mfc42u.dll",
            "msvcp60.dll",
            "msvcrt.dll",
            "SUPERSUB.DLL"
        ]

        for filename in required_files:
            src = os.path.join(self.bin_dir, filename)
            dst = os.path.join(daemon_dir, filename)

            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError as e:
                    # Fallback to hard copy if symlink fails
                    logger.warning(f"Symlink failed for {filename}, copying instead: {e}")
                    shutil.copy2(src, dst)

        logger.debug(f"Provisioned daemon directory: {daemon_dir}")
        return daemon_dir

    def _health_monitor_loop(self) -> None:
        """Background thread for continuous health checks."""
        logger.info("Health monitor loop started")

        while not self.shutdown_event.is_set():
            try:
                # Wait for health_interval or shutdown signal
                if self.shutdown_event.wait(self.health_interval):
                    break  # Shutdown requested

                self._perform_health_checks()

            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}", exc_info=True)

        logger.info("Health monitor loop stopped")

    def _perform_health_checks(self) -> None:
        """Perform health checks on all daemon instances."""
        with self.lock:
            for instance in self.instances:
                if not instance.manager:
                    continue

                # Check for stuck requests (timeout detection)
                if instance.is_processing and instance.request_started_at:
                    elapsed = time.time() - instance.request_started_at
                    request_timeout = 30.0  # 30 second timeout for requests

                    if elapsed > request_timeout:
                        logger.warning(
                            f"Request timeout detected on {instance.id}: "
                            f"request running for {elapsed:.1f}s (timeout: {request_timeout}s)"
                        )
                        # Clear processing flag - request is considered failed
                        instance.is_processing = False
                        instance.request_started_at = None
                        instance.state = "unhealthy"
                        instance.consecutive_failures += 1

                        # Trigger restart if needed
                        if instance.restart_count < self.max_restart_attempts:
                            logger.info(f"Attempting automatic restart of {instance.id} due to stuck request...")
                            self.restart_instance(instance)
                        continue

                try:
                    # Quick health check via daemon manager
                    health_result = instance.manager.health_check()

                    if health_result:
                        # Daemon is healthy
                        instance.state = "healthy"
                        instance.last_health_check = time.time()

                        # Close circuit breaker if it was open
                        if instance.circuit_breaker_open:
                            instance.circuit_breaker_open = False
                            instance.consecutive_failures = 0
                            logger.info(f"Circuit breaker closed for {instance.id} (health check passed)")
                    else:
                        # Daemon unhealthy
                        instance.state = "unhealthy"
                        logger.warning(f"Health check failed for {instance.id}: not healthy")

                except Exception as e:
                    # Health check failed
                    instance.state = "crashed"
                    logger.warning(f"Health check failed for {instance.id}: {e}")

                    # Attempt automatic restart
                    if instance.restart_count < self.max_restart_attempts:
                        logger.info(f"Attempting automatic restart of {instance.id}...")
                        self.restart_instance(instance)
