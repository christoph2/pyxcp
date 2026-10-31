import selectors
import socket

import pytest

import pyxcp.transport.eth as eth_module
import pyxcp.transport.eth_backend as eth_backend
from pyxcp.tests.fake_eth_backend import FakeSocketBackend

# Tests patch ``pyxcp.transport.eth_backend.socket.socket`` / ``...selectors.DefaultSelector``
# to feed the Python test backend with mocked sockets.
eth_backend.socket = socket
eth_backend.selectors = selectors


@pytest.fixture(autouse=True)
def _python_eth_backend(request, monkeypatch):
    """Use the Python test backend, except for tests exercising the native backends."""
    if "native_backend" not in request.node.name:
        monkeypatch.setattr(eth_module, "create_eth_backend", lambda name, eth: FakeSocketBackend(eth))
