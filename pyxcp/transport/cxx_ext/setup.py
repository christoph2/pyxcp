import os
import subprocess  # nosec
import sys
from distutils.core import setup

from pybind11.setup_helpers import Pybind11Extension, build_ext


try:
    INCLUDE_DIRS = subprocess.getoutput("pybind11-config --include")  # nosec
except Exception as e:
    print(f"Error while executing pybind11-config ({e!r}).\npybind11 probably not installed?")
    sys.exit(1)

pf = sys.platform
if pf.startswith("win32"):
    LIBS = ["ws2_32"]
elif pf.startswith("linux"):
    LIBS = ["pthread", "rt"]
else:
    raise RuntimeError(f"Platform {pf!r} currently not supported.")


os.environ["CFLAGS"] = ""

PKG_NAME = "eth_booster"
EXT_NAMES = ["eth_booster"]
__version__ = "0.0.1"

ext_modules = [
    Pybind11Extension(
        EXT_NAMES[0],
        include_dirs=[INCLUDE_DIRS],
        sources=["blocking_socket.cpp", "utils.cpp", "wrap.cpp"],
        define_macros=[("EXTENSION_NAME", EXT_NAMES[0])],
        extra_compile_args=["-O3", "-Wall", "-Weffc++", "-std=c++17"],
        libraries=LIBS,
    ),
]

setup(
    name=PKG_NAME,
    version="0.0.1",
    author="Christoph Schueler",
    description="Example",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
