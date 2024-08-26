#!/usr/bin/env python
"""Lowlevel API reflecting available XCP services

.. note:: For technical reasons the API is split into two parts;
          common methods and a Python version specific part.

.. [1] XCP Specification, Part 2 - Protocol Layer Specification
"""
from .master import Master  # noqa: F401
