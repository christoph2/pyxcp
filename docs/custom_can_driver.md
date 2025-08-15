
### Building an custom CAN driver

[example](pyxcp/blob/master/pyxcp/examples/xcp_user_supplied_driver.py)


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
