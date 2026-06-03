Custom CAN bus objects
----------------------

By default, ``pyXCP`` automatically creates and manages CAN bus objects
for you. In most situations this means you don't need to worry about
setting up the bus manually.

There are three levels of CAN interface integration, ordered from
simplest to most flexible:

1. **python-can plugin interface** — use any driver that registers
   itself via python-can's entry-point plugin system (no wrapper code).
2. **Existing bus object** — pass a pre-created ``can.Bus`` instance
   directly (e.g. shared with another application such as ``UDSonCAN``).
3. **Fully custom interface** — implement ``CanInterfaceBase`` for
   hardware that is not supported by python-can at all.

.. _can-plugin-interface:

python-can plugin interface (recommended for third-party drivers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

python-can ships with a `plugin interface
<https://python-can.readthedocs.io/en/stable/interfaces.html#plugin-interface>`__
that lets external packages register additional CAN drivers via Python
entry points.  Once such a package is installed, its driver is
available to *both* ``can.Bus()`` and — directly to pyxcp — without
any wrapper code.

Simply set ``c.Transport.Can.interface`` to the plugin's registered
name, exactly as you would with ``can.Bus(interface="...")``.

**Example: python-can-remote**

`python-can-remote <https://github.com/christiansandberg/python-can-remote>`__
provides a CAN-over-network bridge and registers under the name
``"remote"``.  Install it with:

.. code:: bash

   pip install python-can-remote

Then configure pyxcp:

.. code:: python

   # pyxcp_conf.py
   c.Transport.layer = "CAN"
   c.Transport.Can.interface     = "remote"           # python-can plugin name
   c.Transport.Can.channel       = "ws://myhost:54701/"
   c.Transport.Can.bitrate       = 500_000
   c.Transport.Can.can_id_master = 0x01
   c.Transport.Can.can_id_slave  = 0x02

pyxcp forwards the common parameters (``channel``, ``bitrate``, ``fd``,
``data_bitrate``, ``receive_own_messages``, ``poll_interval``) to
python-can, which resolves the actual driver via its plugin registry.

Passing driver-specific parameters (``extra_params``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the driver requires keyword arguments beyond the common base set,
use ``c.Transport.Can.CanCustom.extra_params``.  Every entry is merged verbatim into
the ``can.Bus()`` call *after* the standard parameters (and therefore
takes precedence on key overlap):

.. code:: python

   # pyxcp_conf.py
   c.Transport.layer = "CAN"
   c.Transport.Can.interface = "remote"
   c.Transport.Can.channel   = "ws://myhost:54701/"
   c.Transport.Can.bitrate   = 500_000

   # Driver-specific extras forwarded verbatim to can.Bus():
   c.Transport.Can.CanCustom.extra_params = {"rx_queue_size": 128, "proprietary_option": 4711}

Known python-can plugin packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following packages are maintained by third parties.  Issues should
be reported in their respective repositories.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Package / interface name
     - Description
   * - ``python-can-remote`` / ``"remote"``
     - CAN over network bridge
   * - ``python-can-canine`` / ``"canine"``
     - CAN Driver for the CANine CAN interface
   * - ``python-can-cvector`` / ``"cvector"``
     - Cython-based version of the Vector bus
   * - ``python-can-sontheim`` / ``"sontheim"``
     - CAN Driver for Sontheim interfaces (e.g. CANfox)
   * - ``zlgcan`` / ``"zlgcan"``
     - Python wrapper for zlgcan-driver-rs
   * - ``python-can-cando`` / ``"cando"``
     - Python wrapper for Netronics' CANdo and CANdoISO
   * - ``python-can-candle`` / ``"candle"``
     - Full-featured driver for candleLight

.. note::

   Any python-can plugin that correctly registers a ``can.interface``
   entry point will work — the list above is not exhaustive.  See the
   `python-can plugin documentation
   <https://python-can.readthedocs.io/en/stable/interfaces.html#plugin-interface>`__
   for details on writing your own plugin.

.. _can-existing-bus-object:

Using an existing CAN bus object
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you already hold a ``can.Bus`` instance (e.g. shared with
``UDSonCAN`` or another tool running in the same process), pass it
directly via the ``transport_layer_interface`` parameter:

.. code:: python

   import can
   from pyxcp.cmdline import ArgumentParser

   can_if = can.Bus(interface="kvaser", channel="0", fd=False, bitrate=500000)

   ap = ArgumentParser(description="external interface test")
   with ap.run(transport_layer_interface=can_if) as x:
       x.connect()
       x.disconnect()

.. note::

   - It is the user's responsibility to properly initialize and shut
     down the CAN bus interface.
   - pyxcp **merges** its filter configuration with any existing one,
     so make sure no unwanted traffic is forwarded to other
     applications.  The original filter configuration is restored when
     pyxCP exits.

.. _can-custom-interface:

Fully custom interface (hardware not supported by python-can)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your hardware is not supported by python-can at all, implement the
thin ``CanInterfaceBase`` ABC (a subset of python-can's `BusABC
<https://github.com/hardbyte/python-can/blob/bc248e8aaf96280a574c06e8e7d2778a67f091e3/can/bus.py#L46>`__):

.. code:: python

   from pyxcp.transport.can import CanInterfaceBase

Import the base class and implement the required abstract methods:

.. code:: python

   #!/usr/bin/env python
   import can
   from pyxcp.cmdline import ArgumentParser
   from pyxcp.transport.can import CanInterfaceBase


   class WrappedKvaserInterface(CanInterfaceBase):

       def __init__(self):
           self.canif = can.Bus(interface="kvaser", channel="0", bitrate=500000)

       def set_filters(self, filters):
           self.canif.set_filters(filters)

       def recv(self, timeout=None):
           return self.canif.recv(timeout)

       def send(self, msg):
           self.canif.send(msg)

       @property
       def filters(self):
           return self.canif.filters

       @property
       def state(self):
           return self.canif.state

       def close(self):
           self.canif.shutdown()


   custom_interface = WrappedKvaserInterface()

   ap = ArgumentParser(description="Wrapped Kvaser CAN driver.")
   with ap.run(transport_layer_interface=custom_interface) as x:
       x.connect()
       x.disconnect()

   custom_interface.close()

A skeleton example is also available at
`pyxcp/examples/xcp_user_supplied_driver.py
<https://github.com/christoph2/pyxcp/blob/master/pyxcp/examples/xcp_user_supplied_driver.py>`__.
