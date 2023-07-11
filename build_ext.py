import subprocess
from pathlib import Path
from typing import Any
from typing import Dict

from pybind11.setup_helpers import build_ext
from pybind11.setup_helpers import naive_recompile
from pybind11.setup_helpers import ParallelCompile
from pybind11.setup_helpers import Pybind11Extension

# from setuptools_cpp import CMakeExtension, ExtensionBuilder, Pybind11Extension
# ext_modules = [
#    CMakeExtension("pyxcp.recorder", sourcedir="pyxcp/recorder")
# ]

print("Running 'build.py'...")

PYB11_INCLUDE_DIRS = subprocess.check_output(["pybind11-config", "--includes"])
EXT_NAMES = ["rekorder"]

ParallelCompile("NPY_NUM_BUILD_JOBS", needs_recompile=naive_recompile).install()

ext_modules = [
    Pybind11Extension(
        EXT_NAMES[0],
        include_dirs=[PYB11_INCLUDE_DIRS, "pyxcp/recorder"],
        sources=["pyxcp/recorder/lz4.c", "pyxcp/recorder/wrap.cpp"],
        define_macros=[("EXTENSION_NAME", EXT_NAMES[0]), ("NDEBUG", 1)],
        optional=False,
        cxx_std=20,  # Extension will use C++20 generators/coroutines.
    ),
]


def build(setup_kwargs: Dict[str, Any]) -> None:
    setup_kwargs.update(
        {
            "ext_modules": ext_modules,
            "cmd_class": dict(build_ext=Pybind11Extension),
            "zip_safe": False,
        }
    )
