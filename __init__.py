import sys as _sys
import os  as _os
import spinmob



# Get the version
try: exec(spinmob.fun.read_lines(_os.path.join(__path__[0],'setup.py'))[0])
except: __version__ = 'unknown'

# Windows ADALM2000 Drivers
if _sys.platform in ['win32']:
    try:    import libm2k as _m2k
    except:
        _m2k = None
        spinmob._warn('To use an ADALM2000 on Windows, you need to install libm2k with python bindings.')


# OSX ADALM2000 Drivers
elif _sys.platform in ['darwin']:
    spinmob._warn('No ADALM2000 on OSX yet.')
    _m2k = None

# Linux ADALM2000 Drivers
else:
    _sys.path.append(_os.path.join(__path__[0], 'libm2k', 'linux'))
    try: import libm2k as _m2k
    except:
        _m2k = None
        spinmob._warn('To use an ADALM2000 on Linux, you need to install libiio v0.21, and libm2k v0.2.1.')


# Test for VISA
try:    import visa as _v
except:
    spinmob._warn('Visa driver and / or pyvisa not installed. On Windows, consider Rhode & Schwartz VISA or NI-VISA, then pip install pyvisa. On Linux, pip install pyvisa and pyvisa-py')
    _v = None

from . import visa_tools
from . import instruments
from . import data
from . import functions
from . import playground