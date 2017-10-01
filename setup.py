#!/bin/env python

import os
from setuptools import setup, find_packages
from glob import glob

def packagez(base):
    return  ["{0!s}{1!s}{2!s}".format(base, os.path.sep, p) for p in find_packages(base)]

setup(
    name = 'pyxcp',
    version = '0.9.0',
    provides = ['pyxcp'],
    description = "Universal Calibration Protocol for Python",
    author = 'Christoph Schueler',
    author_email = 'cpu12.gems@googlemail.com',
    url = 'http://github.com/pySART/pyxcp',
    packages = packagez('pyccp'),
    install_requires = ['enum34', 'construct', 'future', 'mako'],
    package_dir = {'tests': 'pyxcp/tests'},
    test_suite = "pyxcp.tests"
)

