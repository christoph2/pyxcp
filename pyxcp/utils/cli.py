#!/usr/bin/env python
"""
Reusable command-line parser utilities.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


class StrippingParser:
    """Base class for parsers that can strip recognized arguments from sys.argv.

    This is useful when multiple argument parsers are used in a single process (chained),
    and downstream parsers should not see arguments already handled by an
    upstream parser.
    """

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        """Initialize with an existing ArgumentParser instance."""
        self._parser = parser

    @property
    def parser(self) -> argparse.ArgumentParser:
        """Return the underlying ArgumentParser instance."""
        return self._parser

    def parse_known(self, argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
        """Parse known args from ``argv`` and return (namespace, remaining).

        Does not mutate ``sys.argv``.
        """
        if argv is None:
            argv = sys.argv[1:]
        namespace, remaining = self._parser.parse_known_args(argv)

        # Emulate standard -h/--help behavior if "help" is in the namespace
        if getattr(namespace, "help", False):
            # Print help and exit similarly to ArgumentParser
            # We need a temporary full parser to render standard help including program name
            full = argparse.ArgumentParser(description=self._parser.description)
            for action in self._parser._actions:
                if action.option_strings and action.dest == "help":
                    continue
                full._add_action(action)
            full.print_help()
            sys.exit(0)

        return namespace, list(remaining)

    def strip_from_argv(self, argv: list[str] | None = None) -> None:
        """Remove this parser's recognized options from ``sys.argv`` in-place.

        If ``argv`` is provided, it is treated as a mutable list whose content
        will be replaced with the stripped version (first element preserved as
        program name). If omitted, ``sys.argv`` is modified.
        """
        arg_list = argv if argv is not None else sys.argv
        if not arg_list:
            return
        _, remaining = self.parse_known(arg_list[1:])
        # Rebuild argv with program name + remaining
        prog = arg_list[0]
        arg_list[:] = [prog] + remaining

    def parse_and_strip(self, argv: list[str] | None = None) -> argparse.Namespace:
        """Parse options and strip them from argv; returns the parsed namespace."""
        arg_list = argv if argv is not None else sys.argv
        if not arg_list:
            # Fallback for empty list
            return self.parse_known([])[0]
        namespace, remaining = self.parse_known(arg_list[1:])
        # mutate
        prog = arg_list[0]
        arg_list[:] = [prog] + remaining
        return namespace
