#!/bin/env python

import os
from codecs import open
from distutils.core import setup, Extension
from setuptools import find_packages
import sys

with open(os.path.join('pyxcp', 'version.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[-1].strip().strip('"')
            break

def packagez(base):
    return  ["{0!s}{1!s}{2!s}".format(base, os.path.sep, p) for p in find_packages(base)]

install_reqs = ['construct == 2.8.17', 'mako', 'pyserial']

if sys.version_info.major == 2 or (sys.version_info.major == 3 and sys.version_info.minor < 4):
    install_reqs.extend(['enum34', 'mock'])

setup(
    name = 'pyxcp',
    version = version,
    provides = ['pyxcp'],
    description = "Universal Calibration Protocol for Python",
    author = 'Christoph Schueler',
    author_email = 'cpu12.gems@googlemail.com',
    url = 'https://github.com/christoph2/pyxcp',
    packages = packagez('pyxcp'),

    include_package_data=True,
    install_requires = ['enum34', 'construct >= 2.8', 'mako', 'pyserial'],

    doc_requires = ['numpydoc', 'sphinxcontrib-napoleon'],
    package_dir = {'tests': 'pyxcp/tests'},
tests_require=["pytest", "pytest-runner"],
test_suite = "pyxcp.tests",
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
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)

