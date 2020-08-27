import sys as _sys
import os  as _os
import traceback as _traceback
_p = _traceback.print_last

try:    import spinmob
except: raise Exception('You definitely need to install spinmob to do anything in mcphysics.')

# Add the appropriate paths for different operating systems

# Location of the linux libm2k dll
if not _sys.platform in ['win32', 'darwin']: _sys.path.append(_os.path.join(__path__[0], 'libm2k', 'linux'))

# Get the version
try: exec(spinmob.fun.read_lines(_os.path.join(__path__[0],'setup.py'))[0])
except: __version__ = 'unknown'

# Import all the other semi-optional libraries
def _safe_import(lib):
    try:
        exec('import '+lib)
        return eval(lib)
    except:
        return None

_imageio        = _safe_import('imageio')
_libm2k         = _safe_import('libm2k')
_visa           = _safe_import('visa')
_serial         = _safe_import('serial')
_minimalmodbus  = _safe_import('minimalmodbus')
_sounddevice    = _safe_import('sounddevice')


_debug_enabled = False
def _debug(*a):
    if _debug_enabled:
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

def check_installation():
    """
    Prints out the status of the optional libraries.
    """
    modules = [
        'imageio',
        'lmfit',
        'libm2k',
        'matplotlib',
        'minimalmodbus',
        'numpy',
        'pyqtgraph',
        'OpenGL',
        'scipy',
        'serial',
        'sounddevice',
        'visa',]

    # Try importing them
    installed = []
    missing   = []
    for m in modules:
        try:
            exec('import ' + m)
            if m in ['visa', 'serial', 'OpenGL']: installed.append('py'+m.lower())
            else:                       installed.append(m)
        except:
            if m in ['visa', 'serial', 'OpenGL']: missing.append('py'+m.lower())
            else:                       missing.append(m)

    if len(installed): print('\nINSTALLED\n  '+'\n  '.join(installed))
    if len(missing):   print('\nMISSING\n  '    +'\n  '.join(missing))
    print()

import mcphysics.instruments as instruments
import mcphysics.experiments as experiments
from . import data
from . import functions
from . import playground