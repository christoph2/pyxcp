#!/usr/bin/env python
"""Tests for config discovery and programmatic configuration.

Tests for Issue #260 (Robot Framework) and #211 (library usage).
"""

from pathlib import Path


from pyxcp.config import PyXCP, create_application_from_config, reset_application, set_application


def test_create_application_from_config_minimal():
    """Test creating application with minimal config."""
    app = create_application_from_config()
    assert app is not None
    assert hasattr(app, "general")
    assert hasattr(app, "transport")
    assert hasattr(app, "log")


def test_create_application_from_config_with_dict():
    """Test creating application with config dict."""
    config = {
        "Transport": {
            "CAN": {
                "device": "socketcan",
                "channel": "can0",
                "bitrate": 500000,
            }
        }
    }
    app = create_application_from_config(config)
    assert app is not None
    assert app.transport.can.device == "socketcan"
    assert app.transport.can.channel == "can0"
    assert app.transport.can.bitrate == 500000


def test_set_application():
    """Test setting global application instance."""
    # Reset first
    reset_application()

    app = create_application_from_config()
    set_application(app)

    from pyxcp.config import get_application

    global_app = get_application()
    assert global_app is app

    # Cleanup
    reset_application()


def test_config_discovery_env_var(monkeypatch, tmp_path):
    """Test PYXCP_CONFIG environment variable."""
    # Create temp config file
    config_file = tmp_path / "test_pyxcp_conf.py"
    config_file.write_text(
        """
c = get_config()
c.Transport.CAN.device = "test_device"
c.Transport.CAN.channel = "test_channel"
"""
    )

    # Set environment variable
    monkeypatch.setenv("PYXCP_CONFIG", str(config_file))

    # Create application (should find config via env var)
    app = PyXCP()
    found_path = app._find_config_file("pyxcp_conf.py")
    assert found_path == config_file


def test_config_discovery_cwd(tmp_path, monkeypatch):
    """Test config discovery in current working directory."""
    # Create config in temp directory
    config_file = tmp_path / "pyxcp_conf.py"
    config_file.write_text("c = get_config()")

    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    app = PyXCP()
    found_path = app._find_config_file("pyxcp_conf.py")
    assert found_path is not None
    assert found_path.name == "pyxcp_conf.py"


def test_config_discovery_home(monkeypatch, tmp_path):
    """Test config discovery in user home directory."""
    # Mock home directory
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    pyxcp_dir = fake_home / ".pyxcp"
    pyxcp_dir.mkdir()

    config_file = pyxcp_dir / "pyxcp_conf.py"
    config_file.write_text("c = get_config()")

    # Patch Path.home()
    def mock_home():
        return fake_home

    monkeypatch.setattr(Path, "home", mock_home)

    app = PyXCP()
    found_path = app._find_config_file("pyxcp_conf.py")
    assert found_path == config_file


def test_config_discovery_not_found():
    """Test config discovery returns None when file not found."""
    app = PyXCP()
    found_path = app._find_config_file("nonexistent_config_12345.py")
    assert found_path is None


def test_programmatic_config_no_file_required():
    """Test that programmatic config works without any file."""
    # This should not raise FileNotFoundError
    config = {"Transport": {"CAN": {"device": "virtual"}}}
    app = create_application_from_config(config)

    # Verify config applied
    assert app.transport.can.device == "virtual"

    # Verify it's a valid application
    assert hasattr(app, "log")
    assert app.log is not None
