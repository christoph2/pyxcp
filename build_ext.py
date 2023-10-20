import subprocess  # nosec
from typing import Any, Dict

from pybind11.setup_helpers import ParallelCompile, Pybind11Extension, naive_recompile


print("Running 'build.py'...")

PYB11_INCLUDE_DIRS = subprocess.check_output(["pybind11-config", "--includes"])  # nosec
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
