Using pyXCP Command-Line Tools
==============================

pyXCP provides several command-line tools to help you work with XCP
devices. These tools are installed automatically when you install the
pyXCP package.

Available Command-Line Tools
----------------------------

pyXCP includes the following command-line tools:

1. **pyxcp-probe-can-drivers**: Probes and lists available CAN drivers
   on your system.
2. **xcp-id-scanner**: Scans for XCP slaves on a CAN bus.
3. **xcp-fetch-a2l**: Fetches A2L file from an XCP slave.
4. **xcp-info**: Displays information about an XCP slave.
5. **xcp-profile**: Creates new configuration files and converts legacy
   configuration files.
6. **xcp-examples**: Shows available examples and how to run them.
7. **xmraw-converter**: Converts XMRAW measurement files to other
   formats.

Basic Usage
-----------

All command-line tools follow a similar pattern for specifying the
transport layer and connection parameters:

.. code:: bash

   <tool-name> -t <transport> --config <config-file>

Where: - ``<tool-name>`` is one of the tools listed above -
``<transport>`` is the transport layer (eth, can, usb, sxi) -
``<config-file>`` is the path to a configuration file

Examples
--------

Probe available CAN drivers:

.. code:: bash

   pyxcp-probe-can-drivers

Display information about an XCP slave using Ethernet with Python
configuration (recommended):

.. code:: bash

   xcp-info -t eth --config conf_eth.py

Display information about an XCP slave using Ethernet with legacy TOML
configuration:

.. code:: bash

   xcp-info -t eth --config conf_eth.toml

Scan for XCP slaves on a CAN bus with Python configuration
(recommended):

.. code:: bash

   xcp-id-scanner -t can --config conf_can.py

Scan for XCP slaves on a CAN bus with legacy TOML configuration:

.. code:: bash

   xcp-id-scanner -t can --config conf_can.toml

Convert an XMRAW file to CSV:

.. code:: bash

   xmraw-converter measurement.xmraw -o csv

Using the xcp-profile Tool
--------------------------

The ``xcp-profile`` tool helps you manage configuration files for pyXCP.
It supports two main use cases:

1. **create**: Generate a new Python-based configuration file with all
   available options
2. **convert**: Convert a legacy .json/.toml configuration file to the
   new Python-based format

Create a New Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a new configuration file with all available options:

.. code:: bash

   # Output to a file
   xcp-profile create -o my_config.py

   # Preview in terminal
   xcp-profile create | less
