#!/usr/bin/env python
"""Tests for max_retries configuration option (WP-8 Phase 1)."""

import pytest

from pyxcp.master.errorhandler import Repeater


class TestRepeater:
    """Test Repeater class with max_retries override."""

    def test_infinite_default(self):
        """Test infinite retry (XCP standard, default behavior)."""
        r = Repeater(Repeater.INFINITE)
        # Infinite should always repeat
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is True

    def test_repeat_once(self):
        """Test single repeat (REPEAT = 1)."""
        r = Repeater(Repeater.REPEAT)
        assert r.repeat() is True
        assert r.repeat() is False

    def test_repeat_twice(self):
        """Test double repeat (REPEAT_2_TIMES = 2)."""
        r = Repeater(Repeater.REPEAT_2_TIMES)
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is False

    def test_max_retries_zero(self):
        """Test max_retries=0 (no retries at all)."""
        # Override infinite with max_retries=0
        r = Repeater(Repeater.INFINITE, max_retries=0)
        assert r.repeat() is False

    def test_max_retries_three(self):
        """Test max_retries=3 (three attempts)."""
        # Override infinite with max_retries=3
        r = Repeater(Repeater.INFINITE, max_retries=3)
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is False

    def test_max_retries_negative_one_infinite(self):
        """Test max_retries=-1 (infinite, XCP standard)."""
        r = Repeater(Repeater.REPEAT, max_retries=-1)
        # Should revert to infinite
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is True

    def test_max_retries_none_uses_initial(self):
        """Test max_retries=None (use initial_value)."""
        # No override, use initial value
        r = Repeater(Repeater.REPEAT_2_TIMES, max_retries=None)
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is False

    def test_max_retries_overrides_repeat(self):
        """Test max_retries overrides REPEAT."""
        # REPEAT=1 but max_retries=5 should allow 5 retries
        r = Repeater(Repeater.REPEAT, max_retries=5)
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is True
        assert r.repeat() is False

    def test_max_retries_overrides_repeat_2_times(self):
        """Test max_retries overrides REPEAT_2_TIMES."""
        # REPEAT_2_TIMES=2 but max_retries=1 should allow only 1 retry
        r = Repeater(Repeater.REPEAT_2_TIMES, max_retries=1)
        assert r.repeat() is True
        assert r.repeat() is False


class TestMaxRetriesIntegration:
    """Integration tests for max_retries with real config."""

    def test_config_default(self):
        """Test that default config has max_retries=-1."""
        from pyxcp.config import General

        g = General()
        assert g.max_retries == -1

    def test_config_set_value(self):
        """Test setting max_retries in config."""
        from pyxcp.config import General

        g = General(max_retries=3)
        assert g.max_retries == 3

    def test_config_set_zero(self):
        """Test setting max_retries=0 in config."""
        from pyxcp.config import General

        g = General(max_retries=0)
        assert g.max_retries == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
