#!/usr/bin/env python
"""
Logging configuration for pyxcp.

By default, pyxcp uses NullHandler to avoid interfering with user's logging setup.
Users can configure logging as needed.
"""

import logging

# Get the root pyxcp logger
logger = logging.getLogger("pyxcp")

# Use NullHandler by default - let users configure logging
logger.addHandler(logging.NullHandler())

# Prevent propagation to root logger unless explicitly configured
logger.propagate = True


def setup_logging(level=logging.INFO, format_string=None, handler=None):
    """
    Configure logging for pyxcp.

    Args:
        level: Logging level (default: INFO)
        format_string: Log message format (default: standard format)
        handler: Custom handler (default: StreamHandler)

    Example:
        >>> from pyxcp.logger import setup_logging
        >>> import logging
        >>> setup_logging(level=logging.DEBUG)
    """
    # Remove existing handlers
    for hdlr in logger.handlers[:]:
        logger.removeHandler(hdlr)

    # Create handler
    if handler is None:
        handler = logging.StreamHandler()

    # Set format
    if format_string is None:
        format_string = "%(levelname)s:%(name)s:%(message)s"

    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)

    # Configure logger
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    return logger


# For backwards compatibility
def get_logger(name="pyxcp"):
    """
    Get a logger instance.

    Args:
        name: Logger name (default: 'pyxcp')

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
