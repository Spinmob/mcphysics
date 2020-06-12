import sys as _sys
import os  as _os
if   _sys.platform in ['win32']:  print('No ADALM2000 on Windows yet.')
elif _sys.platform in ['darwin']: print('No ADALM2000 on OSX yet.')
else:                         
    _sys.path.append(_os.path.join(__path__[0], 'libm2k', 'linux'))
    import libm2k as _m2k


from . import visa_tools
from . import instruments
from . import data
from . import functions
from . import playground