# -*- coding: utf-8 -*-

import mcphysics as _mp
import numpy as _n
import spinmob.egg as _egg
import traceback as _traceback
_p = _traceback.print_last
_g = _egg.gui
import spinmob as _s
import time as _time

try:    from . import serial_tools as _serial_tools
except: _serial_tools = _mp.instruments._serial_tools

_debug_enabled = False
_debug = _mp._debug


        
        
    
        


if __name__ == '__main__':
    
    self = arduino()