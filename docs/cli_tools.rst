Command-Line Tools Reference
============================

pyXCP provides command-line tools for XCP device interaction, configuration management, and data conversion. All tools support the Python-based configuration system (v0.26.4+).

Quick Reference
---------------

- ``xcp-info`` – Inspect ECU capabilities
- ``xcp-id-scanner`` – Scan CAN bus for ECUs
- ``xcp-fetch-a2l`` – Download A2L from ECU
- ``xcp-profile`` – Create/convert configs
- ``xcp-examples`` – Copy example scripts
- ``xmraw-converter`` – Convert measurement data
- ``pyxcp-probe-can-drivers`` – List CAN drivers
- (extra) ``xcp-daq-recorder`` – Automated DAQ recording from JSON config

Configuration Methods
---------------------

Method 1: Python config file (recommended)::

   xcp-info -t eth --config my_config.py
   xcp-profile create -o my_config.py

Example transport factory::

   # my_config.py
   def create_transport(parent):
       from pyxcp.transport.eth import Eth
       return Eth(parent, host="192.168.1.100", port=5555, protocol="TCP")

Method 2: Command-line arguments::

   xcp-info -t eth --host 192.168.1.100 --port 5555
   xcp-info -t can --can-interface socketcan --can-channel can0

Method 3: Legacy TOML (deprecated, supported)::

   xcp-info -t eth --config legacy_config.toml
   xcp-profile convert -o new_config.py old_config.toml

Tool Details
------------

xcp-info
^^^^^^^^
Inspect XCP slave capabilities (DAQ/PAG/PGM, IDs, protection).

Usage::

   xcp-info [OPTIONS]

Common options:
- ``--no-daq`` – skip DAQ queries
- ``--no-pag`` – skip paging
- ``--no-pgm`` – skip programming
- ``--no-ids`` – skip ID scanning

Troubleshooting:
- Hangs on DAQ: use ``--no-daq``
- Protection errors: configure seed/key (see :doc:`FAQ`)

xcp-id-scanner
^^^^^^^^^^^^^^
Scan CAN bus for slaves by broadcasting CONNECT.

Usage::

   xcp-id-scanner [OPTIONS]

Notes: generates bus traffic; limited to CAN; typical range 0x700-0x7FF.

xcp-fetch-a2l
^^^^^^^^^^^^^
Download A2L from slave (requires ``FILE_TO_UPLOAD`` and ``UPLOAD`` support).

Usage::

   xcp-fetch-a2l [OPTIONS]

Output: saves filename reported by slave, or ``output.a2l`` fallback.

xcp-profile
^^^^^^^^^^^
Create/convert configuration files.

Usage::

   xcp-profile <create|convert> [OPTIONS]

Subcommands:
- ``create`` – generate Python config template
- ``convert`` – migrate legacy JSON/TOML to Python config

xcp-examples
^^^^^^^^^^^^
List and copy bundled example scripts.

xmraw-converter
^^^^^^^^^^^^^^^
Convert recorder ``.xmraw`` measurement data to CSV/other formats.

pyxcp-probe-can-drivers
^^^^^^^^^^^^^^^^^^^^^^^
List available CAN drivers from python-can backends.
