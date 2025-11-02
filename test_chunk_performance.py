#!/usr/bin/env python3
"""
Performance test for the chunk-fdo endpoint with large FDO files.
Tests to measure if parallelization improvements are working.
"""

import json
import time
import requests
from pathlib import Path

def test_chunk_performance(test_file_path: str, iterations: int = 3):
    """
    Test chunking performance with a large FDO file.

    Args:
        test_file_path: Path to the FDO test file
        iterations: Number of test iterations to average
    """
    print(f"Testing chunk performance with: {test_file_path}")
    print(f"Iterations: {iterations}\n")

    # Read the test file
    with open(test_file_path, 'r') as f:
        fdo_source = f.read()

    print(f"FDO source length: {len(fdo_source)} characters")
    print(f"FDO source lines: {len(fdo_source.splitlines())}\n")

    # Endpoint URL
    url = "http://localhost:8000/chunk-fdo"

    # Test payload
    payload = {
        "fdo_script": fdo_source,
        "enable_parallel": True  # Ensure parallel compilation is enabled
    }

    times = []

    for i in range(iterations):
        print(f"Iteration {i+1}/{iterations}...", end=" ", flush=True)

        start = time.time()
        try:
            response = requests.post(url, json=payload, timeout=120)
            elapsed = time.time() - start

            if response.status_code == 200:
                result = response.json()
                times.append(elapsed)
                print(f"✓ {elapsed:.2f}s - Chunks: {result.get('total_chunks', 'N/A')}")
            else:
                print(f"✗ Error {response.status_code}: {response.text[:200]}")

        except Exception as e:
            elapsed = time.time() - start
            print(f"✗ Failed after {elapsed:.2f}s: {e}")

    # Calculate statistics
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n{'='*60}")
        print(f"Performance Results:")
        print(f"{'='*60}")
        print(f"Average time: {avg_time:.2f}s")
        print(f"Min time:     {min_time:.2f}s")
        print(f"Max time:     {max_time:.2f}s")
        print(f"Variance:     {max_time - min_time:.2f}s")

        # Check pool status
        try:
            health_response = requests.get("http://localhost:8000/health")
            if health_response.status_code == 200:
                health = health_response.json()
                pool_info = health.get('pool', {})
                print(f"\n{'='*60}")
                print(f"Daemon Pool Status:")
                print(f"{'='*60}")
                print(f"Pool enabled:     {pool_info.get('enabled', False)}")
                print(f"Pool size:        {pool_info.get('size', 'N/A')}")
                print(f"Healthy daemons:  {pool_info.get('healthy_instances', 'N/A')}")
                print(f"Health %:         {pool_info.get('health_percentage', 'N/A'):.1f}%")
        except Exception as e:
            print(f"\nCouldn't fetch pool status: {e}")
    else:
        print("\n✗ No successful requests")

if __name__ == "__main__":
    test_file = Path(__file__).parent / "large_dod_test.fdo.txt"

    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        exit(1)

    test_chunk_performance(str(test_file), iterations=3)
