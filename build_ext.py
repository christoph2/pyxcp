#!/usr/bin/env python

import multiprocessing as mp
import os
import platform
import re
import subprocess  # nosec
import sys
import sysconfig
from pathlib import Path
from tempfile import TemporaryDirectory


TOP_DIR = Path(__file__).parent

print("Platform", platform.system())
uname = platform.uname()
if uname.system == "Darwin":
    os.environ["MACOSX_DEPLOYMENT_TARGET"] = "10.13"

VARS = sysconfig.get_config_vars()


def get_python_base() -> str:
    # Applies in this form only to Windows.
    if "base" in VARS and VARS["base"]:
        return VARS["base"]
    if "installed_base" in VARS and VARS["installed_base"]:
        return VARS["installed_base"]


def alternate_libdir(pth: str):
    base = Path(pth).parent
    libdir = Path(base) / "libs"
    if libdir.exists():
        # available_libs = os.listdir(libdir)
        return str(libdir)
    else:
        return ""


def get_py_config() -> dict:
    pynd = VARS["py_version_nodot"]  # Should always be present.
    include = sysconfig.get_path("include")  # Seems to be cross-platform.
    if uname.system == "Windows":
        base = get_python_base()
        library = f"python{pynd}.lib"
        libdir = Path(base) / "libs"
        if libdir.exists():
            available_libs = os.listdir(libdir)
            if library in available_libs:
                libdir = str(libdir)
            else:
                libdir = ""
        else:
            libdir = alternate_libdir(include)
    else:
        library = VARS["LIBRARY"]
        DIR_VARS = ("LIBDIR", "BINLIBDEST", "DESTLIB", "LIBDEST", "MACHDESTLIB", "DESTSHARED", "LIBPL")
        arch = None
        if uname.system == "Linux":
            arch = VARS.get("MULTIARCH", "")
        for dir_var in DIR_VARS:
            dir_name = VARS.get(dir_var)
            if not dir_name:
                continue
            if uname.system == "Darwin":
                full_path = [Path(dir_name) / library]
            elif uname.system == "Linux":
                full_path = [Path(dir_name) / arch / library, Path(dir_name) / library]
            else:
                print("PF?", uname.system)
            for fp in full_path:
                if fp.exists():
                    print(f"found Python library: '{full_path}'")
                    libdir = dir_name
                    break
                # else:
                #    print(f"NOT found: '{full_path}'")
    return dict(exe=sys.executable, include=include, libdir=libdir, library=library)


def banner(msg: str) -> None:
    print("=" * 80)
    print(str.center(msg, 80))
    print("=" * 80)


def build_extension(debug: bool = False, use_temp_dir: bool = False) -> None:
    print("build_ext::build_extension()")

    debug = bool(os.environ.get("DEBUG", 0)) or debug
    cfg = "Debug" if debug else "Release"
    print(f" BUILD-TYPE: {cfg!r}")

    py_cfg = get_py_config()

    cmake_args = [
        f"-DPython3_EXECUTABLE={py_cfg['exe']}",
        f"-DPython3_INCLUDE_DIR={py_cfg['include']}",
        f"-DPython3_LIBRARY={str(Path(py_cfg['libdir']) / Path(py_cfg['library']))}",
        f"-DCMAKE_BUILD_TYPE={cfg}",  # not used on MSVC, but no harm
    ]

    build_args = ["--config Release", "--verbose"]
    # cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 /path/to/src

    if sys.platform.startswith("darwin"):
        # Cross-compile support for macOS - respect ARCHFLAGS if set
        archs = re.findall(r"-arch (\S+)", os.environ.get("ARCHFLAGS", ""))
        if archs:
            cmake_args += ["-DCMAKE_OSX_ARCHITECTURES={}".format(";".join(archs))]

    if use_temp_dir:
        build_temp = Path(TemporaryDirectory(suffix=".build-temp").name) / "extension_it_in"
    else:
        build_temp = Path(".")
    # print("cwd:", os.getcwd(), "build-dir:", build_temp, "top:", str(TOP_DIR))
    if not build_temp.exists():
        build_temp.mkdir(parents=True)

    banner("Step #1: Configure")
    # cmake_args += ["--debug-output"]
    subprocess.run(["cmake", "-S", str(TOP_DIR), *cmake_args], cwd=build_temp, check=True)  # nosec

    cmake_args += [f"--parallel {mp.cpu_count()}"]

    banner("Step #2: Build")
    # build_args += ["-DCMAKE_VERBOSE_MAKEFILE:BOOL=ON"]
    subprocess.run(["cmake", "--build", str(build_temp), *build_args], cwd=TOP_DIR, check=True)  # nosec

    banner("Step #3: Install")
    subprocess.run(["cmake", "--install", "."], cwd=build_temp, check=True)  # nosec
    subprocess.run(["cmake", "--install", build_temp], cwd=TOP_DIR, check=True)  # nosec


if __name__ == "__main__":
    includes = subprocess.getoutput("pybind11-config --cmakedir")  # nosec
    os.environ["pybind11_DIR"] = includes
    build_extension(False)
