import os
import platform
import subprocess  # nosec
import sys
from pathlib import Path
from typing import Any, Dict

import setuptools.command.build_py
import setuptools.command.develop
from pybind11.setup_helpers import (
    ParallelCompile,
    Pybind11Extension,
    build_ext,
    naive_recompile,
)
from setuptools import Distribution


ROOT_DIRPATH = Path(".")

if sys.platform == "darwin":
    os.environ["CC"] = "clang++"
    os.environ["CXX"] = "clang++"

ParallelCompile("NPY_NUM_BUILD_JOBS", needs_recompile=naive_recompile).install()
PYB11_INCLUDE_DIRS = subprocess.check_output(["pybind11-config", "--includes"])  # nosec
EXT_NAMES = ["pyxcp.recorder.rekorder", "pyxcp.cpp_ext.cpp_ext", "pyxcp.daq_stim.stim"]

ext_modules = [
    Pybind11Extension(
        EXT_NAMES[0],
        include_dirs=[PYB11_INCLUDE_DIRS, "pyxcp/recorder", "pyxcp/cpp_ext"],
        sources=["pyxcp/recorder/lz4.c", "pyxcp/recorder/lz4hc.c", "pyxcp/recorder/wrap.cpp"],
        define_macros=[("EXTENSION_NAME", EXT_NAMES[0]), ("NDEBUG", 1)],
        optional=False,
        cxx_std=20,
    ),
    Pybind11Extension(
        EXT_NAMES[1],
        include_dirs=[PYB11_INCLUDE_DIRS, "pyxcp/cpp_ext"],
        sources=["pyxcp/cpp_ext/extension_wrapper.cpp"],
        define_macros=[("EXTENSION_NAME", EXT_NAMES[1]), ("NDEBUG", 1)],
        optional=False,
        cxx_std=20,
    ),
    Pybind11Extension(
        EXT_NAMES[2],
        include_dirs=[PYB11_INCLUDE_DIRS, "pyxcp/daq_stim", "pyxcp/cpp_ext"],
        sources=["pyxcp/daq_stim/stim.cpp", "pyxcp/daq_stim/stim_wrapper.cpp", "pyxcp/daq_stim/scheduler.cpp"],
        define_macros=[("EXTENSION_NAME", EXT_NAMES[2]), ("NDEBUG", 1)],
        optional=False,
        cxx_std=20,  # Extension will use C++20 generators/coroutines.
    ),
]


class AsamKeyDllAutogen(setuptools.Command):
    """Custom command to compile `asamkeydll.exe`."""

    description = "Compile `asamkeydll.exe`."

    def initialize_options(self):
        pass

    def finalize_options(self):
        """Post-process options."""
        asamkeydll = os.path.join("pyxcp", "asamkeydll.c")
        target = os.path.join("pyxcp", "asamkeydll.exe")
        self.arguments = [asamkeydll, f"-o{target}"]

    def run(self):
        """Run gcc"""
        word_width, _ = platform.architecture()
        if sys.platform in ("win32") and word_width == "64bit":
            gccCmd = ["gcc", "-m32", "-O3", "-Wall"]
            self.announce(" ".join(gccCmd + self.arguments))
            try:
                subprocess.check_call(gccCmd + self.arguments)  # nosec
            except Exception as e:
                print(f"Building pyxcp/asamkeydll.exe failed: {e!r}")
            else:
                print("Successfully  build pyxcp/asamkeydll.exe")


class CustomBuildPy(setuptools.command.build_py.build_py):
    def run(self):
        self.run_command("asamkeydll")
        super().run()


class CustomDevelop(setuptools.command.develop.develop):
    def run(self):
        self.run_command("asamkeydll")
        super().run()


def build(setup_kwargs: Dict[str, Any]) -> None:
    setup_kwargs.update(
        {
            "ext_modules": ext_modules,
            "cmd_class": dict(build_ext=Pybind11Extension),
            "zip_safe": False,
        }
    )


def invoke_command(distribution: Distribution, name: str) -> None:
    cmd = distribution.cmdclass.get(name)(distribution)
    print(f"Building target {name!r}...")
    cmd.inplace = 1
    cmd.ensure_finalized()
    cmd.run()


###
if __name__ == "__main__":
    distribution = Distribution(
        {
            "cmdclass": {
                "asam_key_dll": AsamKeyDllAutogen,
                "CXX_extensions": build_ext,
            },
            "name": "pyxcp",
            "ext_modules": ext_modules,
            "package_dir": {"pyxcp": str(ROOT_DIRPATH / "pyxcp")},
        }
    )
    invoke_command(distribution, "CXX_extensions")
    invoke_command(distribution, "asam_key_dll")
