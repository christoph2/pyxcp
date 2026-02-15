Frame Acquisition Policy Migration Guide
=========================================

Overview
--------

pyXCP uses **Frame Acquisition Policies** to handle incoming XCP frames. As of version 0.27.0, the default policy has changed from ``LegacyFrameAcquisitionPolicy`` to ``NoOpPolicy`` to prevent unbounded memory growth.

Why the Change?
---------------

``LegacyFrameAcquisitionPolicy`` suffers from unbounded memory leaks in long-running DAQ sessions:

- **8 unbounded C++ queues** (CMD, RES, EV, SERV, DAQ, META, ERR, STIM)
- **Memory growth**: ~23 MB/hour at 100 Hz DAQ rate
- **24-hour leak**: Nearly 2 GB of accumulated frames
- **Root cause**: Event queue (``evQueue``) grows indefinitely

The policy is explicitly marked as **deprecated** in the C++ code:

.. code-block:: cpp

   /*
       Dequeue based frame acquisition policy.

       Deprecated: Use only for compatibility reasons.
   */

Available Policies
------------------

NoOpPolicy (Default)
~~~~~~~~~~~~~~~~~~~~

**Discards all frames immediately** - No memory footprint, ideal for most use cases where frames are processed in real-time through callbacks.

.. code-block:: python

   from pyxcp.transport.base import NoOpPolicy

   policy = NoOpPolicy(filtered_out=None)
   with ap.run(policy=policy) as x:
       x.connect()
       # Your code here

**Memory**: O(1) - No accumulation

**Use case**: Standard XCP command/response, DAQ with real-time processing


FrameRecorderPolicy (Recommended for Recording)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Streams frames directly to disk** in ``.xmraw`` format - Constant memory usage, high performance.

.. code-block:: python

   from pyxcp.transport.base import FrameRecorderPolicy

   policy = FrameRecorderPolicy("session.xmraw", filtered_out=None)
   with ap.run(policy=policy) as x:
       x.connect()
       # DAQ recording session
       x.disconnect()

**Memory**: O(1) - Frames written to disk immediately

**Use case**: Long-running DAQ recording, post-processing with ``xmraw-converter``


StdoutPolicy (Debug/Development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Prints frames to console** - Useful for debugging transport-layer issues.

.. code-block:: python

   from pyxcp.transport.base import StdoutPolicy

   policy = StdoutPolicy(filtered_out=None)
   with ap.run(policy=policy) as x:
       x.connect()
       # Frames printed to stdout

**Memory**: O(1) - Frames printed immediately

**Use case**: Debugging, development, protocol analysis


PyFrameAcquisitionPolicy (Custom)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Python callback-based** - Maximum flexibility for custom frame processing.

.. code-block:: python

   from pyxcp.transport.base import PyFrameAcquisitionPolicy, FrameCategory

   class MyPolicy(PyFrameAcquisitionPolicy):
       def __init__(self):
           super().__init__(filtered_out=None)
           self.daq_count = 0

       def feed(self, frame_category, counter, timestamp, payload):
           if frame_category == FrameCategory.DAQ:
               self.daq_count += 1
               # Process DAQ frame

       def finalize(self):
           print(f"Processed {self.daq_count} DAQ frames")

   policy = MyPolicy()
   with ap.run(policy=policy) as x:
       x.connect()
       # ...

**Memory**: Depends on implementation

**Use case**: Real-time analytics, custom filtering, live dashboards


LegacyFrameAcquisitionPolicy (Deprecated)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**DO NOT USE** for new code. Retained only for backward compatibility.

.. code-block:: python

   # ⚠️ DEPRECATED - Causes memory leaks!
   from pyxcp.transport.base import LegacyFrameAcquisitionPolicy

   policy = LegacyFrameAcquisitionPolicy(filtered_out=None)
   # DeprecationWarning will be emitted

**Memory**: O(n) - **Unbounded growth** over time

**Known issues**:
- Event queue grows without limit
- 24-hour DAQ session can leak ~2 GB
- Queues never automatically consumed


Migration Checklist
-------------------

If you have existing code using ``LegacyFrameAcquisitionPolicy``:

1. **Identify your use case**:

   - Recording DAQ data → ``FrameRecorderPolicy``
   - Real-time processing → ``PyFrameAcquisitionPolicy``
   - Standard operation → ``NoOpPolicy`` (default)
   - Debugging → ``StdoutPolicy``

2. **Update policy instantiation**:

   .. code-block:: python

      # Before (deprecated)
      from pyxcp.transport.base import LegacyFrameAcquisitionPolicy
      policy = LegacyFrameAcquisitionPolicy(filtered_out=None)

      # After (recommended)
      from pyxcp.transport.base import FrameRecorderPolicy
      policy = FrameRecorderPolicy("recording.xmraw", filtered_out=None)

3. **Remove queue access**:

   Legacy policy exposed queues (``resQueue``, ``daqQueue``, etc.). Modern policies use:

   - **Callbacks**: ``PyFrameAcquisitionPolicy.feed()``
   - **Files**: ``FrameRecorderPolicy`` → read with ``XcpLogFileReader``
   - **Real-time**: Process in DAQ callback, not via queues

4. **Test memory usage**:

   .. code-block:: bash

      # Run your benchmark
      python pyxcp/benchmarks/daq_memory_test.py

      # Should show stable memory (~0 MB/s growth)


Performance Comparison
----------------------

**Validation Tests** (5-minute DAQ simulation @ 100 Hz, 30,000 frames):

==========================  ===============  ==================  =================
Policy                      Memory Growth    24h Extrapolation   Output
==========================  ===============  ==================  =================
LegacyFrameAcquisition      +0.0227 MB/s     **1,958 MB** (leak) In-memory queue
NoOpPolicy (default)        +0.000078 MB/s   **6.75 MB** ✅      Discarded
FrameRecorderPolicy         +0.000911 MB/s   **78.75 MB** ✅     Disk (.xmraw)
StdoutPolicy                ~0 MB/s          ~0 MB ✅            Console
==========================  ===============  ==================  =================

**Key findings:**

- **NoOpPolicy**: 290x reduction in memory leak vs. Legacy (6.75 MB vs 1,958 MB in 24h)
- **FrameRecorderPolicy**: 25x reduction + data persisted to disk
- **Legacy Policy**: Confirmed unbounded growth, ~2 GB leak in 24h @ 100 Hz DAQ

**Validation methodology:**

- Test duration: 5 minutes (300 seconds)
- DAQ rate: 100 Hz (simulated)
- Frames processed: ~27,500-28,000
- Memory sampled every 60 seconds
- Python 3.13, psutil memory tracking
- Validation scripts: ``pyxcp/benchmarks/validation_*.py``


**Backward Compatibility**

**Default behavior change**:

- **Before v0.27.0**: ``LegacyFrameAcquisitionPolicy()`` (implicit)
- **After v0.27.0**: ``NoOpPolicy(filtered_out=None)`` (implicit)

**Breaking change**: Code that relied on accessing ``.daqQueue`` or ``.evQueue`` from the policy will break. Use explicit policy:

.. code-block:: python

   # Temporary compatibility (not recommended)
   from pyxcp.transport.base import LegacyFrameAcquisitionPolicy
   import warnings

   warnings.filterwarnings("ignore", category=DeprecationWarning)
   policy = LegacyFrameAcquisitionPolicy(filtered_out=None)

**Long-term fix**: Migrate to modern callback-based approach.


Examples
--------

See ``pyxcp/examples/xcp_policy.py`` for working examples of all policies.

For recording workflows, see ``pyxcp/examples/daq_recording.py``.


Related Issues
--------------

- `#171 <https://github.com/christophschubert/pyxcp/issues/171>`_ - Memory leak in DAQ mode
- `#218 <https://github.com/christophschubert/pyxcp/issues/218>`_ - Performance optimization opportunities


References
----------

- C++ implementation: ``pyxcp/transport/transport_ext.hpp``
- Python bindings: ``pyxcp/transport/transport_wrapper.cpp``
- Recorder format: ``pyxcp/recorder/`` (xmraw specification)
