# Windows:
#  Install Rhode & Schwarz VISA or NI-VISA
#  pip install pyvisa
#  Name the scope something reasonable in OpenChoice Instrument Manager
#
# Linux
#  pip install pyvisa pyvisa-py
#  Let me know if you find out how to name the scope.

# Feature to implement
#  * Sillyscope: Find trigger time and define this to be zero.
#  * Sillyscope: Option to query full data set

# ISSUES:
# * Rigol B: switching from peak detect to normal in between runs causes acquire button to fail once.
# * ADALM2000 Enabling channels doesn't seem to change the incoming data. Currently it just ignores the disabled ones.
import traceback as _traceback
_p = _traceback.print_last

from . import gui_tools as _gui_tools
from . import serial_tools as _serial_tools

from . import adalm2000  as _adalm2000
adalm2000_api = _adalm2000.adalm2000_api
adalm2000     = _adalm2000.adalm2000

from . import sillyscope as _sillyscope
sillyscope_api = _sillyscope.sillyscope_api
sillyscope     = _sillyscope.sillyscope

from . import keithley_dmm as _keithley_dmm
keithley_dmm_api = _keithley_dmm.keithley_dmm_api
keithley_dmm     = _keithley_dmm.keithley_dmm

from . import auber_syl53x2p as _auber_syl53x2p
auber_syl53x2p_api = _auber_syl53x2p.auber_syl53x2p_api
auber_syl53x2p     = _auber_syl53x2p.auber_syl53x2p

from . import soundcard as _soundcard
soundcard = _soundcard.soundcard

