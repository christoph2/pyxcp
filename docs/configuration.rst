Configuration
=============

pyXCP supports various configuration options for different transport
layers and use cases. This guide explains how to configure pyXCP for
your specific needs.

Configuration Systems
---------------------

pyXCP supports two configuration systems:

1. **Traitlets-based Configuration (Recommended)**: Python-based
   configuration using the traitlets library
2. **Legacy Configuration**: TOML or JSON based configuration
   (deprecated, don’t use in new project)

Traitlets-based Configuration
-----------------------------

The recommended way to configure pyXCP is using Python configuration
files with the traitlets system:

.. code:: python

   # Configuration file for pyXCP
   c = get_config()  # noqa

   # Transport configuration
   c.Transport.layer = "ETH"  # Transport layer: ETH, CAN, USB, SXI

   # Ethernet configuration
   c.Transport.Eth.host = "localhost"
   c.Transport.Eth.port = 5555
   c.Transport.Eth.protocol = "TCP"

You can generate a template configuration file with all available
options:

.. code:: bash

   xcp-profile create -o my_config.py

Legacy Configuration (Deprecated)
---------------------------------

The older TOML and JSON based configuration is still supported but is
now considered legacy:

.. code:: toml

   [XCP]
   # General XCP settings
   TRANSPORT = "ETH"  # Transport layer: ETH, CAN, USB, SXI

   [ETH]
   # Transport-specific settings
   HOST = "localhost"
   PORT = 5555

You can convert a legacy configuration file to the new format:

.. code:: bash

   xcp-profile convert -c old_config.toml -o new_config.py

Transport Layer Configuration
-----------------------------

Ethernet (TCP/IP)
~~~~~~~~~~~~~~~~~

Recommended Python configuration:

.. code:: python

   # Transport configuration
   c.Transport.layer = "ETH"

   # Ethernet configuration
   c.Transport.Eth.host = "localhost"  # IP address or hostname
   c.Transport.Eth.port = 5555         # Port number
   c.Transport.Eth.protocol = "TCP"    # TCP or UDP

Legacy TOML configuration:

.. code:: toml

   [XCP]
   TRANSPORT = "ETH"

   [ETH]
   HOST = "localhost"  # IP address or hostname
   PORT = 5555         # Port number
   PROTOCOL = "TCP"    # TCP or UDP
   LOGLEVEL = "INFO"   # Optional: DEBUG, INFO, WARNING, ERROR, CRITICAL

CAN
~~~

Recommended Python configuration:

.. code:: python

   # Transport configuration
   c.Transport.layer = "CAN"

   # CAN configuration
   c.Transport.Can.interface = "vector"  # CAN interface supported by python-can
   c.Transport.Can.channel = 0           # Channel identification
   c.Transport.Can.bitrate = 500000      # CAN bitrate in bits/s
   c.Transport.Can.can_id_master = 0x7E0 # CAN-ID master -> slave
   c.Transport.Can.can_id_slave = 0x7E1  # CAN-ID slave -> master
   c.Transport.Can.max_dlc_required = False # Master to slave frames always to have DLC = MAX_DLC = 8

Legacy TOML configuration:

.. code:: toml

   [XCP]
   TRANSPORT = "CAN"

   [CAN]
   INTERFACE = "vector"
   CHANNEL = 0
   BITRATE = 500000
   CAN_ID_MASTER = 2016
   CAN_ID_SLAVE = 2017

USB
~~~

.. code:: python

   c.Transport.layer = "USB"
   # Configure USB specifics as supported by your environment

SXI
~~~

.. code:: python

   c.Transport.layer = "SXI"
   # Configure SXI specifics as needed

Additional Notes
----------------

- Prefer Python/traitlets configuration for new projects.
- Use ``xcp-profile create`` to bootstrap a config and
  ``xcp-profile convert`` to migrate legacy TOML/JSON.
- Ensure the chosen transport layer matches any externally provided
  interface (e.g., if passing a pre-created CAN interface, set
  ``c.Transport.layer = 'CAN'``).
