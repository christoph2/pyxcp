
## Custom CAN bus objects

By default, `pyXCP` automatically creates and manages CAN bus objects for you.

In most situations, this means you don’t need to worry about setting up the bus manually.

There are, however, two special cases where you might want to provide your own CAN bus object instead:

- You are already working with a CAN bus object in another application, such as `UDSonCAN`.

- You need to use an interface that is not supported by [python-can](https://github.com/hardbyte/python-can).

In these situations, `pyXCP` allows you to integrate your existing setup rather than creating a new one.
The following examples illustrate how you can pass your own CAN bus object to `pyXCP`:


### Using an existing CAN bus object

```python
import can

from pyxcp.cmdline import ArgumentParser

can_if = can.Bus(interface="kvaser", channel="0", fd=False, bitrate=500000)

ap = ArgumentParser(description="external interface test")

with ap.run(transport_layer_interface=can_if) as x:
	x.connect()
	x.disconnect()
```

### Using an unsupported interface

If your CAN interface is not supported by python-can, you can still integrate it by writing minimal wrapper code that provides the methods `pyXCP` requires (e.g. send() and recv()).

This is done by implementing the interface `CanInterfaceBase` (basically a subset of python-can's [BusABC](https://github.com/hardbyte/python-can/blob/bc248e8aaf96280a574c06e8e7d2778a67f091e3/can/bus.py#L46)).


```python
class CanInterfaceBase(ABC):
    """
    Base class for custom CAN interfaces.
    This is basically a subset of python-CANs `BusABC`.
    """

    @abstractmethod
    def set_filters(self, filters: Optional[List[Dict[str, Union[int, bool]]]] = None) -> None:
        """Apply filtering to all messages received by this Bus.

        filters:
            A list of dictionaries, each containing a 'can_id', 'can_mask', and 'extended' field, e.g.:
            [{"can_id": 0x11, "can_mask": 0x21, "extended": False}]
        """

    @abstractmethod
    def recv(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Block waiting for a message from the Bus."""

    @abstractmethod
    def send(self, msg: Message) -> None:
        """Transmit a message to the CAN bus."""

    @property
    @abstractmethod
    def filters(self) -> Optional[List[Dict[str, Union[int, bool]]]]:
        """Modify the filters of this bus."""

    @property
    @abstractmethod
    def state(self) -> BusState:
        """Return the current state of the hardware."""
```

Import it as follows:
```python
from pyxcp.transport.can import CanInterfaceBase
```

Use this [example](pyxcp/blob/master/pyxcp/examples/xcp_user_supplied_driver.py) as a starting point, or the following sucessfully tested code:

```python
#!/usr/bin/env python

import can

from pyxcp.cmdline import ArgumentParser
from pyxcp.transport.can import CanInterfaceBase


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


custom_interface = WrappedKvaserInterface()

ap = ArgumentParser(description="Wrapped Kvaser CAN driver.")
with ap.run(transport_layer_interface=custom_interface) as x:
    x.connect()
    x.disconnect()

custom_interface.close()
```

In both variants, you pass your CAN bus object to the `run()` method via the `transport_layer_interface` parameter.

Some important notes:
- It is the user’s responsibility to properly initialize and shut down the CAN bus interface.
- In addition, `pyXCP` merges its filter configuration with the existing one, so users must ensure that no unwanted traffic is passed to the external application. The original filter configuration is restored when `pyXCP` exits.
- Choose "custom" as your CAN interface:
 ```python
 c.Transport.Can.interface="custom"
 ```
