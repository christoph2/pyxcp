#!/bin/env python

import distutils
import os
import platform
from setuptools import command, find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
import subprocess
import sys

with open(os.path.join('pyxcp', 'version.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[-1].strip().strip('"')
            break

with open("README.md", "r") as fh:
    long_description = fh.read()

install_reqs = [
    'pyusb', 'construct >= 2.9.0', 'mako', 'pyserial', 'toml', ]
setup_reqs = [
    'pyusb', 'construct >= 2.9.0', 'mako', 'pyserial', 'toml', ]

class AsamKeyDllAutogen(distutils.cmd.Command):
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
            self.announce(" ".join(gccCmd + self.arguments), level = distutils.log.INFO)
            try:
                subprocess.check_call(gccCmd + self.arguments)
            except Exception as e:
                print("Building pyxcp/asamkeydll.exe failed: '{}'".format(str(e)))
            else:
                print("Successfully  build pyxcp/asamkeydll.exe")

class CustomBuildPy(command.build_py.build_py):

    def run(self):
        self.run_command("asamkeydll")
        super().run()

class CustomDevelop(command.develop.develop):

    def run(self):
        self.run_command("asamkeydll")
        super().run()

setup(
    name='pyxcp',
    version=version,
    provides=['pyxcp'],
    description="Universal Calibration Protocol for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Christoph Schueler',
    author_email='cpu12.gems@googlemail.com',
    url='https://github.com/christoph2/pyxcp',
    packages=find_packages(),
    cmdclass={
        "asamkeydll": AsamKeyDllAutogen,
        "build_py": CustomBuildPy,
        "develop": CustomDevelop,
    },
    include_package_data=True,
    install_requires=install_reqs,
    setup_requires=setup_reqs,
    extras_require={
       "docs": [
           'sphinxcontrib-napoleon'
       ],
        "develop": [
            "bumpversion"
       ]
    } ,
    package_dir={'tests': 'pyxcp/tests'},
    tests_require=["pytest", "pytest-runner"],
    test_suite="pyxcp.tests",
    license='GPLv2',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
