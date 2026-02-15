Logging Configuration
=====================

Overview
--------

``pyxcp`` uses Python's standard ``logging`` module with a **NullHandler by default** to avoid interfering with your application's logging configuration.

This follows Python's logging best practices for libraries: **libraries should never configure logging**, only applications should.

Default Behavior
----------------

By default, ``pyxcp`` produces **no log output**:

.. code-block:: python

   from pyxcp.cmdline import ArgumentParser

   ap = ArgumentParser(description="Silent by default")
   with ap.run() as xcp:
       xcp.connect()
       # No logging output unless you configure it
       xcp.disconnect()

This ensures pyxcp doesn't interfere with your own logging setup.


Logger Hierarchy
----------------

``pyxcp`` uses a hierarchical logger structure:

.. code-block:: text

   pyxcp                         # Root logger (NullHandler)
   ├── pyxcp.master              # Master class logs
   │   └── pyxcp.master.errorhandler  # Error handling logs
   ├── pyxcp.transport           # Transport layer logs
   ├── pyxcp.daq_stim            # DAQ/STIM logs
   └── pyxcp.recorder.converter  # Recorder logs

All loggers inherit from the ``pyxcp`` root logger, so configuring the root affects all child loggers.


Enabling Logging
----------------

Method 1: Quick Setup (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the built-in ``setup_logging()`` helper:

.. code-block:: python

   from pyxcp.logger import setup_logging
   import logging

   # Enable INFO logging to console
   setup_logging(level=logging.INFO)

   # Now pyxcp logs will appear
   from pyxcp.cmdline import ArgumentParser
   ap = ArgumentParser(description="With logging")
   with ap.run() as xcp:
       xcp.connect()  # Will log connection details
       xcp.disconnect()


Method 2: Standard Python Logging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure using Python's standard logging:

.. code-block:: python

   import logging

   # Configure root logger for your application
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
   )

   # pyxcp logs will now appear with 'pyxcp.*' names
   from pyxcp.cmdline import ArgumentParser
   ap = ArgumentParser(description="Standard logging")
   with ap.run() as xcp:
       xcp.connect()
       xcp.disconnect()


Method 3: File Logging
~~~~~~~~~~~~~~~~~~~~~~~

Log to file instead of console:

.. code-block:: python

   import logging

   # Create file handler
   handler = logging.FileHandler("pyxcp_session.log", mode="w")
   formatter = logging.Formatter(
       "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s"
   )
   handler.setFormatter(formatter)

   # Configure pyxcp logger
   pyxcp_logger = logging.getLogger("pyxcp")
   pyxcp_logger.addHandler(handler)
   pyxcp_logger.setLevel(logging.DEBUG)

   # All pyxcp activity logged to file
   from pyxcp.cmdline import ArgumentParser
   ap = ArgumentParser(description="File logging")
   with ap.run() as xcp:
       xcp.connect()
       xcp.disconnect()


Method 4: Selective Module Logging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable logging for specific pyxcp modules only:

.. code-block:: python

   import logging

   logging.basicConfig(level=logging.WARNING)  # App default: warnings only

   # But enable DEBUG for transport layer only
   transport_logger = logging.getLogger("pyxcp.transport")
   transport_logger.setLevel(logging.DEBUG)

   # Now only transport logs at DEBUG, rest at WARNING
   from pyxcp.cmdline import ArgumentParser
   ap = ArgumentParser(description="Selective logging")
   with ap.run() as xcp:
       xcp.connect()  # Transport DEBUG logs appear
       xcp.disconnect()


Advanced Configuration
----------------------

Multiple Handlers
~~~~~~~~~~~~~~~~~

Send logs to multiple destinations:

.. code-block:: python

   import logging

   pyxcp_logger = logging.getLogger("pyxcp")
   pyxcp_logger.setLevel(logging.DEBUG)

   # Console handler (INFO and above)
   console = logging.StreamHandler()
   console.setLevel(logging.INFO)
   console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
   pyxcp_logger.addHandler(console)

   # File handler (DEBUG and above)
   file_handler = logging.FileHandler("pyxcp_debug.log")
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(logging.Formatter(
       "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
   ))
   pyxcp_logger.addHandler(file_handler)

   # INFO+ to console, DEBUG+ to file


Custom Formatting
~~~~~~~~~~~~~~~~~

Use custom log format for pyxcp:

.. code-block:: python

   import logging

   # Custom format with milliseconds and function name
   formatter = logging.Formatter(
       "%(asctime)s.%(msecs)03d [%(name)s:%(funcName)s] %(levelname)s: %(message)s",
       datefmt="%H:%M:%S"
   )

   handler = logging.StreamHandler()
   handler.setFormatter(formatter)

   pyxcp_logger = logging.getLogger("pyxcp")
   pyxcp_logger.addHandler(handler)
   pyxcp_logger.setLevel(logging.DEBUG)


Integration with Existing Loggers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your application already has logging configured, pyxcp will inherit it:

.. code-block:: python

   import logging

   # Your application's logging setup
   logging.basicConfig(
       level=logging.INFO,
       format="[%(levelname)s] %(name)s: %(message)s",
       handlers=[
           logging.FileHandler("app.log"),
           logging.StreamHandler()
       ]
   )

   # pyxcp logs will automatically use your configuration
   from pyxcp.cmdline import ArgumentParser
   ap = ArgumentParser(description="Integrated logging")
   with ap.run() as xcp:
       xcp.connect()  # Logs to app.log and console
       xcp.disconnect()


Logging Levels
--------------

``pyxcp`` uses standard Python logging levels:

========  ======================================================================
Level     Usage
========  ======================================================================
DEBUG     Detailed diagnostic information (frame contents, state transitions)
INFO      General informational messages (connection established, DAQ started)
WARNING   Something unexpected but not critical (timeout, retry)
ERROR     Error occurred but operation continues (command failed)
CRITICAL  Serious error, operation cannot continue
========  ======================================================================

**Recommended levels:**

- **Production**: ``WARNING`` or ``ERROR`` only
- **Development**: ``INFO`` for general visibility
- **Debugging**: ``DEBUG`` for detailed protocol traces


Troubleshooting
---------------

"No logs appearing"
~~~~~~~~~~~~~~~~~~~

1. **Check handler is configured**:

   .. code-block:: python

      import logging
      pyxcp_logger = logging.getLogger("pyxcp")
      print(f"Handlers: {pyxcp_logger.handlers}")  # Should not be empty

2. **Check log level**:

   .. code-block:: python

      import logging
      pyxcp_logger = logging.getLogger("pyxcp")
      print(f"Level: {logging.getLevelName(pyxcp_logger.level)}")

3. **Check propagation**:

   .. code-block:: python

      import logging
      pyxcp_logger = logging.getLogger("pyxcp")
      print(f"Propagate: {pyxcp_logger.propagate}")  # Should be True


"ValueError: I/O operation on closed file" (Issue #176)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause**: Your application's file handler was closed while pyxcp tried to log.

**Solution**: Ensure proper shutdown order:

.. code-block:: python

   import logging

   # Your logging setup
   file_handler = logging.FileHandler("myapp.log")
   logger = logging.getLogger("myapp")
   logger.addHandler(file_handler)

   # Use pyxcp
   from pyxcp.cmdline import ArgumentParser
   with ap.run() as xcp:
       xcp.connect()
       xcp.disconnect()

   # Close file handler AFTER pyxcp is done
   file_handler.close()
   logger.removeHandler(file_handler)


"Logs duplicated"
~~~~~~~~~~~~~~~~~

**Cause**: Multiple handlers registered or propagation issues.

**Solution**: Clear existing handlers before reconfiguring:

.. code-block:: python

   import logging

   pyxcp_logger = logging.getLogger("pyxcp")

   # Clear existing handlers
   for handler in pyxcp_logger.handlers[:]:
       pyxcp_logger.removeHandler(handler)

   # Add your handler
   new_handler = logging.StreamHandler()
   pyxcp_logger.addHandler(new_handler)


Examples
--------

Minimal Debug Session
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pyxcp.logger import setup_logging
   from pyxcp.cmdline import ArgumentParser
   import logging

   # Quick debug setup
   setup_logging(level=logging.DEBUG)

   ap = ArgumentParser(description="Debug session")
   with ap.run() as xcp:
       xcp.connect()
       result = xcp.fetch(0x1000, 4)
       print(f"Data: {result.hex()}")
       xcp.disconnect()


Production with File Rotation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Rotating file handler (10 MB max, 5 backups)
   handler = RotatingFileHandler(
       "pyxcp.log",
       maxBytes=10*1024*1024,
       backupCount=5
   )
   formatter = logging.Formatter(
       "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
   )
   handler.setFormatter(formatter)

   pyxcp_logger = logging.getLogger("pyxcp")
   pyxcp_logger.addHandler(handler)
   pyxcp_logger.setLevel(logging.WARNING)  # Production: warnings only


Multi-Application Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging

   # Application logger
   app_logger = logging.getLogger("myapp")
   app_logger.setLevel(logging.INFO)

   # pyxcp logger (child of root)
   pyxcp_logger = logging.getLogger("pyxcp")
   pyxcp_logger.setLevel(logging.WARNING)  # Less verbose than app

   # Shared handler
   handler = logging.StreamHandler()
   handler.setFormatter(logging.Formatter(
       "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
   ))

   # Add to both
   app_logger.addHandler(handler)
   # pyxcp inherits from root, so configure root too
   logging.root.addHandler(handler)
   logging.root.setLevel(logging.INFO)


FAQ
---

**Q: Why doesn't pyxcp log anything by default?**

A: Following Python best practices, libraries should not configure logging. Only applications should. This prevents pyxcp from interfering with your logging setup.

**Q: How do I enable verbose logging for debugging?**

A: Use ``setup_logging(level=logging.DEBUG)`` from ``pyxcp.logger``.

**Q: Can I use different log levels for different pyxcp modules?**

A: Yes! Configure loggers like ``logging.getLogger("pyxcp.transport").setLevel(logging.DEBUG)``.

**Q: Does pyxcp use print() statements?**

A: No. All output uses proper logging (except for CLI tools which use ``rich.console``).

**Q: Can I disable logging completely?**

A: It's already disabled by default (NullHandler). If you see logs, it's because you or another library configured logging.

**Q: How do I log to syslog/network/database?**

A: Use Python's standard logging handlers (``SysLogHandler``, ``SocketHandler``, etc.) with the ``pyxcp`` logger.


Related Documentation
---------------------

- :doc:`troubleshooting` - Common errors and solutions
- :doc:`configuration` - Configuration system
- Python logging documentation: https://docs.python.org/3/library/logging.html
- Logging HOWTO: https://docs.python.org/3/howto/logging.html


References
----------

**Issue #176**: User logging configuration conflict

**Python logging best practices for libraries**:

- Use NullHandler by default
- Never call ``logging.basicConfig()`` in library code
- Use hierarchical logger names
- Let applications configure logging
