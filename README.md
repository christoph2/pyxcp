# pyXCP

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/85f774708b2542d98d02df55c743d24a)](https://app.codacy.com/app/christoph2/pyxcp?utm_source=github.com&utm_medium=referral&utm_content=christoph2/pyxcp&utm_campaign=Badge_Grade_Settings)
[![Maintainability](https://api.codeclimate.com/v1/badges/4c639f3695f2725e392a/maintainability)](https://codeclimate.com/github/christoph2/pyxcp/maintainability)
[![Build Status](https://github.com/christoph2/pyxcp/workflows/Python%20application/badge.svg)](https://github.com/christoph2/pyxcp/actions)
[![Build status](https://ci.appveyor.com/api/projects/status/r00l4i4co095e9ht?svg=true)](https://ci.appveyor.com/project/christoph2/pyxcp)
[![Coverage Status](https://coveralls.io/repos/github/christoph2/pyxcp/badge.svg?branch=master)](https://coveralls.io/github/christoph2/pyxcp?branch=master)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GPL License](http://img.shields.io/badge/license-GPL-blue.svg)](http://opensource.org/licenses/GPL-2.0)

pyXCP is a lightweight Python library which talks to ASAM MCD-1 XCP enabled devices.
These are mainly, but not only, automotive ECUs (Electronic Control Units).

XCP is used to take measurements, to adjust parameters, and to flash during the development process.

XCP also replaces the older CCP (CAN Calibration Protocol).

---

## Installation

pyXCP is hosted on Github, get the latest release: [https://github.com/christoph2/pyxcp](https://github.com/christoph2/pyxcp)

You can install pyxcp from source:

```
pip install -r requirements.txt
python setup.py install
```

Alternatively, you can install pyxcp from source with pip:

```
pip install git+https://github.com/christoph2/pyxcp.git
```

Alternatively, get pyxcp from [PyPI](https://pypi.org/project/pyxcp/):

```
pip install pyxcp
```

### Requirements

- Python >= 3.7
- A running XCP slave (of course).
- If you are using a 64bit Windows version and want to use seed-and-key .dlls (to unlock resources), a GCC compiler capable of creating 32bit
  executables is required:

  These .dlls almost always ship as 32bit versions, but you can't load a 32bit .dll into a 64bit process, so a small bridging program (asamkeydll.exe) is
  required.

## First steps

T.B.D.

## Features

T.B.D.

## References

- [Offical home of XCP](https://www.asam.net/standards/detail/mcd-1-xcp/)

## License

GNU Lesser General Public License v3 or later (LGPLv3+)
