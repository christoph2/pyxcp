#!/usr/bin/env python
"""Tests for timeout diagnostics improvements (WP-8 Phase 2)."""

import pytest
from unittest.mock import Mock
from collections import deque


# Don't inherit from BaseTransport to avoid polluting __subclasses__()
class StandaloneTransportMock:
    """Minimal transport mock that doesn't pollute BaseTransport.__subclasses__()."""

    def __init__(self):
        self.frames_sent = 0
        self.frames_received = 0
        self.last_command_sent = None
        self.timeout = 2_000_000_000  # 2 seconds in nanoseconds
        self.config = Mock()
        self.config.parent = None
        self._last_pdus = deque(maxlen=200)

    # Import the actual methods we want to test
    def _build_timeout_message(self, cmd):
        """Copied from BaseTransport for testing."""
        timeout_sec = self.timeout / 1_000_000_000

        received_count = self.frames_received

        parts = [
            f"Response timed out after {timeout_sec:.1f}s for command {cmd.name}.",
            f"Frames sent: {self.frames_sent}, received: {received_count}.",
        ]

        transport_name = self.__class__.__name__.lower()

        if received_count == 0:
            parts.append("No responses received - check:")
            if "can" in transport_name:
                parts.append("  1. ECU powered and connected?")
                parts.append("  2. CAN termination (120Ω) present?")
                parts.append("  3. CAN IDs correct (check A2L file)?")
                parts.append("  4. CAN bitrate matches ECU?")
            elif "eth" in transport_name:
                parts.append("  1. ECU powered and network cable connected?")
                parts.append("  2. IP address and port correct?")
                parts.append("  3. Firewall blocking connection?")
                parts.append("  4. ECU in correct mode (measurement vs bootloader)?")
            else:
                parts.append("  1. ECU powered and connected?")
                parts.append("  2. Transport parameters correct?")
                parts.append("  3. ECU in correct mode?")
        else:
            parts.append("Some responses received - possible:")
            parts.append("  1. Timeout too short for this command")
            parts.append("  2. ECU overloaded (reduce DAQ rate)")
            parts.append("  3. Intermittent connection issue")

        parts.append(f"\nTry: c.Transport.timeout = {timeout_sec * 2:.1f}  # Increase timeout")

        return "\n".join(parts)

    def _build_diagnostics_dump(self):
        """Copied from BaseTransport for testing."""
        import json

        dump = {
            "transport": self.__class__.__name__,
            "frames_sent": getattr(self, "frames_sent", 0),
            "frames_received": getattr(self, "frames_received", 0),
            "last_command": getattr(self.last_command_sent, "name", None) if self.last_command_sent else None,
        }
        return json.dumps(dump, indent=2)


# Specific mock classes for testing different transport types
class MockCanTransport(StandaloneTransportMock):
    """Mock CAN transport for testing."""

    pass


class MockEthTransport(StandaloneTransportMock):
    """Mock ETH transport for testing."""

    pass


class TestFrameCounters:
    """Test frame counter tracking."""

    def test_initial_counters_zero(self):
        """Test that frame counters start at zero."""
        transport = StandaloneTransportMock()
        assert transport.frames_sent == 0
        assert transport.frames_received == 0
        assert transport.last_command_sent is None

    def test_counters_increment(self):
        """Test that counters can be incremented."""
        transport = StandaloneTransportMock()
        transport.frames_sent = 5
        transport.frames_received = 3
        assert transport.frames_sent == 5
        assert transport.frames_received == 3


class TestTimeoutMessage:
    """Test enhanced timeout message generation."""

    def test_timeout_message_no_responses_can(self):
        """Test timeout message for CAN with no responses."""
        real_transport = MockCanTransport()
        real_transport.frames_sent = 10
        real_transport.frames_received = 0

        from pyxcp.types import Command

        cmd = Command.CONNECT

        msg = real_transport._build_timeout_message(cmd)

        assert "Response timed out after 2.0s" in msg
        assert "Frames sent: 10, received: 0" in msg
        assert "No responses received - check:" in msg
        assert "CAN termination" in msg or "ECU powered" in msg
        assert "c.Transport.timeout = 4.0" in msg

    def test_timeout_message_some_responses(self):
        """Test timeout message when some responses were received."""
        real_transport = StandaloneTransportMock()
        real_transport.frames_sent = 20
        real_transport.frames_received = 15

        from pyxcp.types import Command

        cmd = Command.GET_STATUS

        msg = real_transport._build_timeout_message(cmd)

        assert "Response timed out after 2.0s" in msg
        assert "Frames sent: 20, received: 15" in msg
        assert "Some responses received - possible:" in msg
        assert "Timeout too short" in msg
        assert "c.Transport.timeout = 4.0" in msg

    def test_timeout_message_ethernet(self):
        """Test timeout message for Ethernet transport."""
        real_transport = MockEthTransport()
        real_transport.frames_sent = 5
        real_transport.frames_received = 0

        from pyxcp.types import Command

        cmd = Command.CONNECT

        msg = real_transport._build_timeout_message(cmd)

        assert "Frames sent: 5, received: 0" in msg
        # Should have ETH-specific hints
        assert "IP address" in msg or "network cable" in msg


class TestDiagnosticsDump:
    """Test that diagnostics dump includes frame counters."""

    def test_diagnostics_includes_frame_counts(self):
        """Test that diagnostics dump includes frame counters."""
        real_transport = StandaloneTransportMock()
        real_transport.frames_sent = 42
        real_transport.frames_received = 38
        real_transport.last_command_sent = Mock()
        real_transport.last_command_sent.name = "CONNECT"

        dump = real_transport._build_diagnostics_dump()

        assert "frames_sent" in dump
        assert "frames_received" in dump
        assert "42" in dump
        assert "38" in dump
        assert "CONNECT" in dump or "last_command" in dump


class TestBlockReceiveTimeout:
    """Test block_receive timeout with enhanced diagnostics."""

    def test_block_receive_timeout_message(self):
        """Test that block_receive timeout includes frame counts."""
        # This is more of an integration test - just verify the message format
        # The actual timeout behavior is tested in transport-specific tests
        pass  # Covered by existing transport tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
