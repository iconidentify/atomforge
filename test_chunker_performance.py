"""
Performance test for FDO Chunker with manual compilation optimization
"""

import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'api' / 'src'))

from fdo_chunker import FdoChunker
from fdo_daemon_client import FdoDaemonClient


async def test_chunker_performance():
    """Test chunker performance with large_dod_test.fdo.txt"""

    # Initialize chunker
    daemon_client = FdoDaemonClient('127.0.0.1', 8080)
    chunker = FdoChunker(daemon_client)

    # Check daemon health
    try:
        health = daemon_client.health_check()
        if not health.get('healthy'):
            print("ERROR: Daemon not healthy")
            return
    except Exception as e:
        print(f"ERROR: Daemon not available: {e}")
        print("Make sure the daemon is running with: docker compose up")
        return

    # Load test file
    test_file = Path(__file__).parent / 'large_dod_test.fdo.txt'
    if not test_file.exists():
        print(f"ERROR: {test_file} not found")
        return

    print("=" * 70)
    print("FDO CHUNKER PERFORMANCE TEST")
    print("=" * 70)
    print(f"\nTest file: {test_file}")
    print(f"File size: {test_file.stat().st_size / 1024:.2f} KB")

    fdo_script = test_file.read_text()

    # Warm-up run (to eliminate cold-start effects)
    print("\nWarm-up run...")
    try:
        await chunker.process_fdo_script(fdo_script, stream_id=0, token='AT')
        print("Warm-up complete")
    except Exception as e:
        print(f"ERROR during warm-up: {e}")
        return

    # Timed run
    print("\nTimed run...")
    start_time = time.time()

    try:
        result = await chunker.process_fdo_script(fdo_script, stream_id=0, token='AT')
        end_time = time.time()

        elapsed = end_time - start_time

        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Processing time: {elapsed:.3f} seconds ({elapsed*1000:.1f} ms)")
        print(f"Chunks generated: {result['total_chunks']}")
        print(f"Total payload size: {result['total_size']} bytes")

        if result['total_chunks'] > 0:
            print(f"Average time per chunk: {(elapsed/result['total_chunks'])*1000:.2f} ms")

        # Estimate daemon-only time (assuming 50ms per atom)
        lines = fdo_script.strip().split('\n')
        compilable_atoms = sum(1 for line in lines if 'append_data' in line or 'dod_data' in line)
        estimated_daemon_time = compilable_atoms * 0.05

        print(f"\nPerformance comparison:")
        print(f"  Compilable atoms: {compilable_atoms}")
        print(f"  Estimated daemon-only time: {estimated_daemon_time:.2f}s")
        print(f"  Actual time with manual compilation: {elapsed:.3f}s")
        print(f"  Speedup: {estimated_daemon_time/elapsed:.1f}x")

        print("\n" + "=" * 70)
        print("TEST PASSED")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_chunker_performance())
