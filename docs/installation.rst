Installation and Getting Started
================================

**Python**: *Python* >= 3.11, < 3.16

**Platforms**: No platform-specific restrictions besides availability of
communication drivers (CAN, Ethernet, USB, etc.).

**Documentation**: `Latest documentation <https://pyxcp.rtfd.org>`__

Installation Methods
--------------------

From PyPI
~~~~~~~~~

.. code:: bash

   pip install pyxcp

From Source
~~~~~~~~~~~

.. code:: bash

   # Clone the repository
   git clone https://github.com/christoph2/pyxcp.git
   cd pyxcp

   # Install dependencies
   pip install -r requirements.txt

   # Install the package
   python setup.py install

Using pip with GitHub
~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   pip install git+https://github.com/christoph2/pyxcp.git

Requirements
------------

- Python >= 3.11, < 3.16
- A running XCP slave (of course)
- If you are using a 64-bit Windows version and want to use seed-and-key
  .dlls (to unlock resources), a GCC compiler capable of creating 32-bit
  executables is required. These .dlls almost always ship as 32-bit
  versions, but you can’t load a 32-bit .dll into a 64-bit process, so a
  small bridging program (asamkeydll.exe) is required.
