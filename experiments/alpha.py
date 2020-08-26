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


class alpha_arduino(_serial_tools.arduino_base):
    """
    Class for talking to the Arduino used to control the Alpha experiments.
    """

    def __init__(self, name='alpha_arduino'):
        
        # Run the base arduino stuff
        _serial_tools.arduino_base.__init__(self, name=name)
        
        # Tab area
        self.tabs = self.serial_gui_base.grid_bot.add(_g.TabArea(
            autosettings_path=name+'.tabs'))
        self.tab_raw = self.tabs.add_tab('Raw')
        self.tab_cal = self.tabs.add_tab('Calibrated')
        
        
        ###################################
        ## RAW TAB
        
        
        
        # Plot raw
        self.tab_raw.plot = self.tab_raw.add(_g.DataboxPlot(
            autosettings_path = name+'.tab_raw.plot',
            name              = name+'.tab_raw.plot'), alignment=0)
        
        self.tab_raw.new_autorow()
        
        self.tab_raw.grid_history = self.tab_raw.add(_g.GridLayout(margins=False))
        self.tab_raw.grid_history.add(_g.Label('History:'))
        self.tab_raw.number_history = self.tab_raw.grid_history.add(_g.NumberBox(
            value=0, step=100, bounds=(0,None), int=True,
            autosettings_path = name+'.tab_raw.number_history', 
            tip = 'How many data points to keep in the plot. Zero means "keep errthing".'))
        
        ####################################
        ## CAL TAB
        
        # Settings
        sr = self.tab_cal.settings = self.tab_cal.add(_g.TreeDictionary(
            autosettings_path = name+'.tab_cal.settings',
            name              = name+'.tab_cal.settings',
            new_parameter_signal_changed=self._settings_cal_changed)).set_width(230)
        
        
        # Plot cal
        self.tab_cal.plot = self.tab_cal.add(_g.DataboxPlot(
            autosettings_path = name+'.tab_cal.plot',
            name              = name+'.tab_cal.plot'), alignment=0)
        
        
        ######################################
        ## OTHER STUFF
        
        # Timer for querying arduino state
        self.timer = _g.Timer(500)
        self.timer.signal_tick.connect(self._timer_tick)
        self.t_connect = None
        
        # Run stuff after connecting.
        self.serial_gui_base._after_button_connect_toggled = self._after_button_connect_toggled
    
    def get_voltage_raw(self, n=1):
        """
        Returns the nominal (raw) voltage at Arduino channel n.
        """
        if self.api.simulation_mode: return _n.random.rand()
        else:                        return float(self.api.query('VOLTAGE'+str(int(n))+'?'))
    
    def _after_button_connect_toggled(self, *a):
        """
        Called after the connect button is toggled.
        """
        # Shortcut.
        self.api = self.serial_gui_base.api
        
        # If connected
        if self.serial_gui_base.button_connect():
            self.timer.start()
            if self.t_connect is None: self.t_connect = _time.time()
        
        # Disconnected
        else:
            self.timer.stop()
    
    def _settings_cal_changed(self, *a):
        """
        Called when one of the cal settings changes.
        """
        print(a)
    
    def _timer_tick(self, *a):
        """
        Called when the update timer ticks.
        """
        # Get the next data point.
        V1 = self.get_voltage_raw(1)
        if V1 is None: 
            #print('Could not get V1.')
            return
        
        V2 = self.get_voltage_raw(2)
        if V2 is None:
            #print('Could not get V2.')
            return
        
        self.tab_raw.plot.append_row(
            [_time.time()-self.t_connect, V1, V2],
            ['t', 'V1', 'V2'], 
            history = int(self.tab_raw.number_history())).plot()


if __name__ == '__main__':
    
    self = alpha_arduino()