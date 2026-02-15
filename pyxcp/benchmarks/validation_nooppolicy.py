#!/usr/bin/env python
"""
WP-6 Phase 4: Long-running validation test for NoOpPolicy.

This script validates that NoOpPolicy (new default) has constant memory usage
during extended DAQ operation, confirming the memory leak fix.

Expected result: Memory growth ~0 MB over 1 hour (vs. ~136 MB with Legacy).
"""

import gc
import time
from collections import deque

import psutil


def get_memory_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def simulate_daq_with_nooppolicy(duration_seconds=3600, daq_rate_hz=100):
    """
    Simulate DAQ mode with NoOpPolicy for specified duration.

    Parameters
    ----------
    duration_seconds : int
        Test duration (default: 3600 = 1 hour)
    daq_rate_hz : int
        Simulated DAQ frame rate in Hz

    Returns
    -------
    dict
        Test results including memory measurements
    """
    # Import after baseline measurement
    from pyxcp.transport import NoOpPolicy
    from pyxcp.transport.transport_ext import FrameCategory

    print("=" * 80)
    print("WP-6 Phase 4: NoOpPolicy Validation Test")
    print("=" * 80)
    print(f"Duration: {duration_seconds}s ({duration_seconds / 3600:.1f}h)")
    print(f"DAQ Rate: {daq_rate_hz} Hz")
    print(f"Expected frames: {duration_seconds * daq_rate_hz:,}")
    print()

    # Create policy
    policy = NoOpPolicy(filtered_out=None)

    # Baseline measurement
    gc.collect()
    time.sleep(1)
    initial_memory = get_memory_mb()
    print(f"Initial memory: {initial_memory:.2f} MB")

    # Simulate DAQ frames
    frame_interval = 1.0 / daq_rate_hz
    start_time = time.time()
    frame_count = 0
    memory_samples = deque(maxlen=100)  # Keep last 100 samples

    # Sample memory every 60 seconds
    next_sample_time = start_time + 60

    print("\nRunning test... (samples every 60s)")
    print("Time(s)  Memory(MB)  Delta(MB)  Rate(MB/s)  Frames")
    print("-" * 70)

    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            if elapsed >= duration_seconds:
                break

            # Simulate frame processing (NoOpPolicy discards immediately)
            frame_category = FrameCategory.DAQ
            counter = frame_count
            timestamp = int(current_time * 1_000_000)  # microseconds
            payload = "\x00" * 32  # String, not bytes (C++ expects std::string_view)

            # Feed to policy (NoOpPolicy.feed() is empty, O(1))
            policy.feed(frame_category, counter, timestamp, payload)
            frame_count += 1

            # Sleep to maintain rate
            time.sleep(frame_interval)

            # Memory sampling
            if current_time >= next_sample_time:
                current_memory = get_memory_mb()
                delta = current_memory - initial_memory
                rate = delta / elapsed if elapsed > 0 else 0
                memory_samples.append((elapsed, current_memory))

                print(f"{elapsed:7.0f}  {current_memory:10.2f}  {delta:9.2f}  {rate:10.6f}  {frame_count:,}")

                next_sample_time += 60

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        elapsed = time.time() - start_time

    # Final measurement
    gc.collect()
    time.sleep(1)
    final_memory = get_memory_mb()
    total_delta = final_memory - initial_memory
    growth_rate = total_delta / elapsed if elapsed > 0 else 0

    # Calculate 24-hour extrapolation
    extrapolated_24h = growth_rate * 86400

    print("-" * 70)
    print("\nTest Results:")
    print("=" * 80)
    print(f"Duration:           {elapsed:.1f}s ({elapsed / 3600:.2f}h)")
    print(f"Frames processed:   {frame_count:,}")
    print(f"Initial memory:     {initial_memory:.2f} MB")
    print(f"Final memory:       {final_memory:.2f} MB")
    print(f"Total growth:       {total_delta:.2f} MB")
    print(f"Growth rate:        {growth_rate:.6f} MB/s")
    print(f"24h extrapolation:  {extrapolated_24h:.2f} MB")
    print()

    # Verdict
    if abs(growth_rate) < 0.001:  # < 1 KB/s
        verdict = "✅ PASS - Memory stable (constant)"
    elif abs(growth_rate) < 0.01:  # < 10 KB/s
        verdict = "⚠️  MARGINAL - Small growth detected"
    else:
        verdict = f"❌ FAIL - Memory leak detected ({extrapolated_24h:.0f} MB in 24h)"

    print(f"Verdict: {verdict}")
    print("=" * 80)

    return {
        "duration_seconds": elapsed,
        "frame_count": frame_count,
        "initial_memory_mb": initial_memory,
        "final_memory_mb": final_memory,
        "growth_mb": total_delta,
        "growth_rate_mb_per_sec": growth_rate,
        "extrapolated_24h_mb": extrapolated_24h,
        "verdict": verdict,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NoOpPolicy validation test")
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Test duration in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument("--rate", type=int, default=100, help="DAQ rate in Hz (default: 100)")

    args = parser.parse_args()

    # Run validation
    results = simulate_daq_with_nooppolicy(args.duration, args.rate)

    # Save results
    import json

    with open("validation_nooppolicy_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to: validation_nooppolicy_results.json")
