#!/usr/bin/env python3
"""
FDO Daemon Pool Client

Client with automatic failover and retry logic for daemon pool.
Provides same interface as FdoDaemonClient for backward compatibility.
"""

import time
import logging
from typing import Dict, Any, Callable, Optional

from fdo_daemon_client import FdoDaemonClient, FdoDaemonError
from fdo_daemon_pool_manager import FdoDaemonPoolManager, DaemonInstance

logger = logging.getLogger(__name__)


class FdoDaemonPoolClient:
    """
    Client for FDO daemon pool with automatic failover and retry.

    Provides the same interface as FdoDaemonClient but distributes requests
    across a pool of daemon instances with automatic failover on failure.
    """

    def __init__(
        self,
        pool_manager: FdoDaemonPoolManager,
        max_retries: int = 3,
        timeout_seconds: float = 10.0,
    ):
        """
        Initialize pool client.

        Args:
            pool_manager: FdoDaemonPoolManager instance
            max_retries: Maximum retry attempts per request
            timeout_seconds: Timeout for individual daemon requests
        """
        self.pool_manager = pool_manager
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        logger.info(f"Initialized FdoDaemonPoolClient: max_retries={max_retries}, timeout={timeout_seconds}s")

    def health(self) -> Dict[str, Any]:
        """
        Get aggregate health from all daemon instances.

        Returns:
            Dict with pool health status
        """
        pool_status = self.pool_manager.get_pool_status()

        healthy_count = pool_status["instances_healthy"]
        total_count = pool_status["instances_total"]

        return {
            "healthy": healthy_count > 0,
            "pool_enabled": True,
            "pool_size": total_count,
            "instances_healthy": healthy_count,
            "pool_health_percentage": pool_status["pool_health_percentage"]
        }

    def health_check(self) -> Dict[str, Any]:
        """Alias for health() for compatibility."""
        return self.health()

    async def compile_source(self, source_text: str) -> bytes:
        """
        Compile FDO source with automatic failover.

        Args:
            source_text: FDO source code

        Returns:
            Compiled binary data

        Raises:
            RuntimeError: If all retry attempts fail
        """
        def operation(client: FdoDaemonClient) -> bytes:
            result = client.compile_source(source_text)
            if isinstance(result, dict) and result.get('success'):
                # Convert from dict response to bytes
                return bytes.fromhex(result['binary_data'])
            elif isinstance(result, bytes):
                return result
            else:
                raise FdoDaemonError(f"Unexpected compile response: {type(result)}")

        return await self._execute_with_retry(operation)

    async def decompile_binary(self, binary_data: bytes) -> str:
        """
        Decompile FDO binary with automatic failover.

        Args:
            binary_data: Compiled FDO binary

        Returns:
            FDO source text

        Raises:
            RuntimeError: If all retry attempts fail
        """
        def operation(client: FdoDaemonClient) -> str:
            result = client.decompile_binary(binary_data)
            if isinstance(result, dict) and result.get('success'):
                return result['source_text']
            elif isinstance(result, str):
                return result
            else:
                raise FdoDaemonError(f"Unexpected decompile response: {type(result)}")

        return await self._execute_with_retry(operation)

    async def _execute_with_retry(self, operation: Callable[[FdoDaemonClient], Any]) -> Any:
        """
        Execute operation with automatic retry and failover.

        Args:
            operation: Function that takes FdoDaemonClient and returns result

        Returns:
            Result from successful operation

        Raises:
            RuntimeError: If no healthy daemons or all retries fail
        """
        attempts = 0
        last_error = None
        attempted_instances = set()

        while attempts < self.max_retries:
            # Get next healthy daemon instance (wait up to 5 seconds if pool is busy)
            instance = await self.pool_manager.get_healthy_instance_async(timeout=5.0)

            if not instance:
                raise RuntimeError(
                    f"No healthy daemon instances available after 5s wait "
                    f"(attempted {len(attempted_instances)} instances, pool exhausted)"
                )

            # Skip if we've already tried this instance
            if instance.id in attempted_instances:
                attempts += 1
                continue

            attempted_instances.add(instance.id)

            # Create client for this daemon instance
            client = FdoDaemonClient(
                base_url=f"http://{instance.bind_host}:{instance.port}",
                timeout_seconds=self.timeout_seconds
            )

            try:
                # Execute operation
                logger.debug(f"Executing operation on {instance.id} (attempt {attempts + 1}/{self.max_retries})")

                try:
                    result = operation(client)

                    # Success - update metrics
                    with self.pool_manager.lock:
                        instance.total_requests += 1
                        instance.consecutive_failures = 0

                        # Close circuit breaker if it was open
                        if instance.circuit_breaker_open:
                            instance.circuit_breaker_open = False
                            logger.info(f"Circuit breaker closed for {instance.id} (successful request)")

                    logger.debug(f"Operation successful on {instance.id}")
                    return result

                except Exception as e:
                    # Failure - update metrics and circuit breaker
                    with self.pool_manager.lock:
                        instance.total_requests += 1
                        instance.failed_requests += 1
                        instance.consecutive_failures += 1

                        # Open circuit breaker if threshold exceeded
                        if instance.consecutive_failures >= self.pool_manager.circuit_breaker_threshold:
                            instance.circuit_breaker_open = True
                            instance.state = "unhealthy"
                            logger.warning(
                                f"Circuit breaker opened for {instance.id} "
                                f"({instance.consecutive_failures} consecutive failures)"
                            )

                    last_error = e
                    attempts += 1

                    logger.warning(f"Operation failed on {instance.id}: {e}")

                    # Exponential backoff before retry (except on last attempt)
                    if attempts < self.max_retries:
                        import asyncio
                        backoff_delay = 0.1 * (2 ** attempts)
                        logger.debug(f"Retry backoff: {backoff_delay:.2f}s")
                        await asyncio.sleep(backoff_delay)

                finally:
                    # Always clear processing flag when done (success or failure)
                    with self.pool_manager.lock:
                        instance.is_processing = False
                        instance.request_started_at = None

            except Exception:
                # Outer try-except catches any unexpected errors
                # Processing flag already cleared in inner finally
                raise

        # All retries exhausted
        raise RuntimeError(
            f"All retry attempts failed ({self.max_retries} attempts across {len(attempted_instances)} instances). "
            f"Last error: {last_error}"
        )

    def __repr__(self) -> str:
        pool_status = self.pool_manager.get_pool_status()
        healthy = pool_status["instances_healthy"]
        total = pool_status["instances_total"]
        return f"FdoDaemonPoolClient(healthy={healthy}/{total}, retries={self.max_retries})"
