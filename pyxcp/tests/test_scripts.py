"""Console script contract tests."""

import importlib
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import toml as tomllib


def test_poetry_console_scripts_import_callable_main():
    pyproject = Path(__file__).parents[2] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text())["tool"]["poetry"]["scripts"]

    for name, target in scripts.items():
        module_name, separator, attr_name = target.partition(":")
        assert separator, f"{name} target must use module:attr format"
        module = importlib.import_module(module_name)
        assert callable(getattr(module, attr_name, None)), f"{name} target {target} must expose callable"
