#!/bin/env python

import os
from setuptools import setup, find_packages
import sys

def packagez(base):
    return  ["{0!s}{1!s}{2!s}".format(base, os.path.sep, p) for p in find_packages(base)]

install_reqs = ['construct == 2.8.17', 'mako', 'pyserial']

if sys.version_info.major == 2 or (sys.version_info.major == 3 and sys.version_info.minor < 4):
    install_reqs.extend(['enum34', 'mock'])

setup(
    name = 'pyxcp',
    version = '0.9.0',
    provides = ['pyxcp'],
    description = "Universal Calibration Protocol for Python",
    author = 'Christoph Schueler',
    author_email = 'cpu12.gems@googlemail.com',
    url = 'http://github.com/pySART/pyxcp',
    packages = packagez('pyxcp'),
    install_requires = install_reqs,
    doc_requires = ['numpydoc', 'sphinxcontrib-napoleon'],
    package_dir = {'tests': 'pyxcp/tests'},
    test_suite = "pyxcp.tests"
)

