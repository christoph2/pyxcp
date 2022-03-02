#!/bin/env python
import os
import platform
import subprocess
import sys

import setuptools.command.build_py
import setuptools.command.develop

try:
    from pybind11.setup_helpers import (
        Pybind11Extension,
        build_ext,
        ParallelCompile,
        naive_recompile,
    )
except ImportError:
    print("package 'pybind11' not installed, could not build recorder extension module.")
    has_pybind11 = False
else:
    has_pybind11 = True
    ParallelCompile("NPY_NUM_BUILD_JOBS", needs_recompile=naive_recompile).install()

try:
    PYB11_INCLUDE_DIRS = subprocess.check_output(["pybind11-config", "--includes"])
except Exception as e:
    print(str(e), end=" -- ")
    has_pybind11 = False
    print("'pybind11-config' not properly working, could not build recorder extension module.")

with open(os.path.join("pyxcp", "__init__.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[-1].strip().strip('"')
            break

with open("README.md", "r") as fh:
    long_description = fh.read()


EXT_NAMES = ["rekorder"]

if has_pybind11:

    ext_modules = [
        Pybind11Extension(
            EXT_NAMES[0],
            include_dirs=[PYB11_INCLUDE_DIRS, "pyxcp/recorder"],
            sources=["pyxcp/recorder/lz4.cpp", "pyxcp/recorder/wrap.cpp"],
            define_macros=[("EXTENSION_NAME", EXT_NAMES[0]), ("NDEBUG", 1)],
            optional=False,
            cxx_std="17",
        ),
    ]
else:
    ext_modules = []

install_reqs = [
    "pybind11",
    "pyusb",
    "construct >= 2.9.0",
    "mako",
    "pyserial",
    "toml",
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
        self.arguments = [asamkeydll, "-o{}".format(target)]

    def run(self):
        """Run gcc"""
        word_width, _ = platform.architecture()
        if sys.platform == "win32" and word_width == "64bit":
            gccCmd = ["gcc", "-m32", "-O3", "-Wall"]
            self.announce(" ".join(gccCmd + self.arguments))
            try:
                subprocess.check_call(gccCmd + self.arguments)
            except Exception as e:
                print("Building pyxcp/asamkeydll.exe failed: '{}'".format(str(e)))
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


setuptools.setup(
    name="pyxcp",
    version=version,
    provides=["pyxcp"],
    description="Universal Calibration Protocol for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Christoph Schueler",
    author_email="cpu12.gems@googlemail.com",
    url="https://github.com/christoph2/pyxcp",
    packages=setuptools.find_packages(),
    cmdclass={
        "asamkeydll": AsamKeyDllAutogen,
        "build_py": CustomBuildPy,
        "develop": CustomDevelop,
    },
    python_requires=">=3.6",
    include_package_data=True,
    install_requires=install_reqs,
    extras_require={"docs": ["sphinxcontrib-napoleon"], "develop": ["bumpversion"]},
    ext_modules=ext_modules,
    package_dir={"tests": "pyxcp/tests"},
    zip_safe=False,
    tests_require=["pytest", "pytest-runner"],
    test_suite="pyxcp.tests",
    license="LGPLv3+",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Topic :: Scientific/Engineering",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
