# How-to build your own CAN drivers

By default, pyXCP automatically creates and manages CAN bus objects for you. In most situations, this means you don't need to worry about setting up the bus manually.

There are, however, two special cases where you might want to provide your own CAN bus object instead:

- You are already working with a CAN bus object in another application, such as UDSonCAN.
- You need to use an interface that is not supported by [python-can](https://github.com/hardbyte/python-can).

In these situations, pyXCP allows you to integrate your existing setup rather than creating a new one.

## Using an existing CAN bus object

```python
import can
from pyxcp.cmdline import ArgumentParser

# Create your CAN bus object
can_if = can.Bus(interface="kvaser", channel="0", fd=False, bitrate=500000)

# Pass it to pyXCP
ap = ArgumentParser(description="external interface test")
with ap.run(transport_layer_interface=can_if) as x:
    x.connect()
    x.disconnect()
```

## Using an unsupported interface

If your CAN interface is not supported by python-can, you can still integrate it by writing minimal wrapper code that provides the methods pyXCP requires (e.g. send() and recv()).

This is done by implementing the interface `CanInterfaceBase` (basically a subset of python-can's [BusABC](https://github.com/hardbyte/python-can/blob/bc248e8aaf96280a574c06e8e7d2778a67f091e3/can/bus.py#L46)).

```python
from pyxcp.transport.can import CanInterfaceBase
import can

class WrappedKvaserInterface(CanInterfaceBase):

    def __init__(self):
        self.canif = can.Bus(interface="kvaser", channel="0", bitrate=500000)

    def set_filters(self, filters):
        self.canif.set_filters(filters)

    def recv(self, timeout: float = None):
        return self.canif.recv(timeout)

    def send(self, msg: can.message.Message):
        self.canif.send(msg)

    @property
    def filters(self):
        return self.canif.filters

    @property
    def state(self):
        return self.canif.state

    def close(self):
        self.canif.shutdown()


# Create your custom interface
custom_interface = WrappedKvaserInterface()

# Pass it to pyXCP
ap = ArgumentParser(description="Wrapped Kvaser CAN driver.")
with ap.run(transport_layer_interface=custom_interface) as x:
    x.connect()
    x.disconnect()

# Don't forget to close your interface
custom_interface.close()
```

## Important Notes

- It is the user's responsibility to properly initialize and shut down the CAN bus interface.
- pyXCP merges its filter configuration with the existing one, so users must ensure that no unwanted traffic is passed to the external application. The original filter configuration is restored when pyXCP exits.
- Choose "custom" as your CAN interface in your configuration:

  ```python
  c.Transport.Can.interface = "custom"
  ```
