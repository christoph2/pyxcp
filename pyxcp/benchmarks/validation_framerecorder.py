#!/usr/bin/env python
"""
WP-6 Phase 4: Long-running validation test for FrameRecorderPolicy.

This script validates that FrameRecorderPolicy has constant memory usage
during extended DAQ operation (frames streamed to disk).

Expected result: Memory growth ~0 MB over 1 hour, data saved to .xmraw file.
"""

import gc
import os
import time
from collections import deque

import psutil


def get_memory_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def get_file_size_mb(filename):
    """Get file size in MB."""
    if os.path.exists(filename):
        return os.path.getsize(filename) / 1024 / 1024
    return 0


def simulate_daq_with_framerecorder(duration_seconds=3600, daq_rate_hz=100):
    """
    Simulate DAQ mode with FrameRecorderPolicy for specified duration.

    Parameters
    ----------
    duration_seconds : int
        Test duration (default: 3600 = 1 hour)
    daq_rate_hz : int
        Simulated DAQ frame rate in Hz

    Returns
    -------
    dict
        Test results including memory and disk measurements
    """
    # Import after baseline measurement
    from pyxcp.transport import FrameRecorderPolicy
    from pyxcp.transport.transport_ext import FrameCategory

    output_file = "validation_recording.xmraw"

    # Clean up old file
    if os.path.exists(output_file):
        os.remove(output_file)

    print("=" * 80)
    print("WP-6 Phase 4: FrameRecorderPolicy Validation Test")
    print("=" * 80)
    print(f"Duration: {duration_seconds}s ({duration_seconds / 3600:.1f}h)")
    print(f"DAQ Rate: {daq_rate_hz} Hz")
    print(f"Expected frames: {duration_seconds * daq_rate_hz:,}")
    print(f"Output file: {output_file}")
    print()

    # Create policy
    policy = FrameRecorderPolicy(output_file, filtered_out=None)

    # Baseline measurement
    gc.collect()
    time.sleep(1)
    initial_memory = get_memory_mb()
    print(f"Initial memory: {initial_memory:.2f} MB")

    # Simulate DAQ frames
    frame_interval = 1.0 / daq_rate_hz
    start_time = time.time()
    frame_count = 0
    memory_samples = deque(maxlen=100)

    # Sample every 60 seconds
    next_sample_time = start_time + 60

    print("\nRunning test... (samples every 60s)")
    print("Time(s)  Memory(MB)  Delta(MB)  File(MB)  Frames")
    print("-" * 70)

    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            if elapsed >= duration_seconds:
                break

            # Simulate frame processing
            frame_category = FrameCategory.DAQ
            counter = frame_count
            timestamp = int(current_time * 1_000_000)  # microseconds
            payload = "\x00" * 32  # String, not bytes

            # Feed to policy (streams to disk)
            policy.feed(frame_category, counter, timestamp, payload)
            frame_count += 1

            # Sleep to maintain rate
            time.sleep(frame_interval)

            # Memory sampling
            if current_time >= next_sample_time:
                current_memory = get_memory_mb()
                delta = current_memory - initial_memory
                file_size = get_file_size_mb(output_file)
                memory_samples.append((elapsed, current_memory))

                print(f"{elapsed:7.0f}  {current_memory:10.2f}  {delta:9.2f}  {file_size:8.2f}  {frame_count:,}")

                next_sample_time += 60

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        elapsed = time.time() - start_time
    finally:
        # Finalize recording
        policy.finalize()

    # Final measurement
    gc.collect()
    time.sleep(1)
    final_memory = get_memory_mb()
    final_file_size = get_file_size_mb(output_file)
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
    print(f"Recording size:     {final_file_size:.2f} MB")
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
        "recording_size_mb": final_file_size,
        "verdict": verdict,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FrameRecorderPolicy validation test")
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Test duration in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument("--rate", type=int, default=100, help="DAQ rate in Hz (default: 100)")

    args = parser.parse_args()

    # Run validation
    results = simulate_daq_with_framerecorder(args.duration, args.rate)

    # Save results
    import json

    with open("validation_framerecorder_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to: validation_framerecorder_results.json")
    print("Recording file: validation_recording.xmraw")
