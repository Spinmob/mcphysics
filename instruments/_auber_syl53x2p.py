# -*- coding: utf-8 -*-

import mcphysics as _mp
import numpy as _n
import spinmob.egg as _egg
import traceback as _traceback
_p = _traceback.print_last
_g = _egg.gui
import spinmob as _s
import time as _time

try:    from . import _serial_tools
except: _serial_tools = _mp.instruments._serial_tools

_debug_enabled = False
_debug = _mp._debug

class auber_syl53x2p_api():
    """
    Commands-only object for interacting with an Auber Instruments SYL-53X2P
    temperature controller.

    Parameters
    ----------
    port='COM3' : str
        Name of the port to connect to.

    address=1 : int
        Address of the instrument. Can be 0-255, and must match the instrument
        setting.

    baudrate=9600 : int
        Baud rate of the connection. Must match the instrument setting.

    timeout=2000 : number
        How long to wait for responses before giving up (ms). Must be >300 for this instrument.
    """
    def __init__(self, port='COM3', address=1, baudrate=9600, timeout=2000):

        # Check for installed libraries
        if not _mp._minimalmodbus or not _mp._serial:
            _s._warn('You need to install pyserial and minimalmodbus to use the Auber SYL-53X2P.')
            self.modbus = None
            self.simulation_mode = True

        # Assume everything will work for now
        else: self.simulation_mode = False

        # If the port is "Simulation"
        if port=='Simulation': self.simulation_mode = True

        # If we have all the libraries, try connecting.
        if not self.simulation_mode:
            try:
                # Create the instrument and ensure the settings are correct.
                self.modbus = _mp._minimalmodbus.Instrument(port, address)

                # Other settings
                self.modbus.serial.baudrate = baudrate              # Baud rate
                self.modbus.serial.bytesize = 8                     # Typical size of a byte :)
                self.modbus.serial.parity = _mp._minimalmodbus.serial.PARITY_NONE # No parity check for this instrument.
                self.modbus.serial.stopbits = 1                     # Whatever this means. It needs to be 1 for this instrument.
                self.modbus.serial.timeout  = timeout*0.001         # Timeout in seconds. Must be >0.3 for this instrument.
                self.modbus.mode = _mp._minimalmodbus.MODE_RTU                    # RTU or ASCII mode. Must be RTU for this instrument.
                self.modbus.clear_buffers_before_each_transaction = True # Seems like a good idea. Works, too.

                # Simulation mode flag
                self.simulation_mode = False

                # Test the connection
                self.get_temperature()


            # Something went wrong. Go into simulation mode.
            except Exception as e:
                print('Could not open connection to "'+port+':'+str(address)+'" at baudrate '+str(baudrate)+'. Entering simulation mode.')
                print(e)
                self.modbus = None
                self.simulation_mode = True

    def disconnect(self):
        """
        Disconnects.
        """
        if not self.simulation_mode: self.modbus.serial.close()

    def get_alarm_status(self):
        """
        Returns the alarm code:

            0: Alarm 1 off, Alarm 2 off (yay!)
            1: Alarm 1 on,  Alarm 2 off
            2: Alarm 1 off, Alarm 2 on
            3: Alarm 1 on,  Alarm 2 on

        It was binary all along! All along!
        """
        if self.simulation_mode: return 0
        else:                    return self.modbus.read_register(0x1201, 0)

    def get_main_output_power(self):
        """
        Gets the current output power (percent).
        """
        if self.simulation_mode: return _n.random.randint(0,200)
        else:                    return self.modbus.read_register(0x1101, 0)

    def get_temperature(self):
        """
        Gets the current temperature in Celcius.
        """
        if self.simulation_mode: return _n.round(_n.random.rand()+24, 1)
        else:                    return self.modbus.read_register(0x1001, 1)

    def get_temperature_setpoint(self):
        """
        Gets the current temperature setpoint in Celcius.
        """
        if self.simulation_mode: return 24.5
        else:                    return self.modbus.read_register(0x1002, 1)

    def set_temperature_setpoint(self, T=20.0):
        """
        Sets the temperature setpoint to the supplied value in Celcius.
        """
        if not self.simulation_mode:
            self.modbus.write_register(0x00, T, number_of_decimals=1, functioncode=6)
            return T
        return self.get_temperature_setpoint()


class auber_syl53x2p(_serial_tools.serial_gui_base):
    """
    Graphical interface for the Auber SYL-53X2P temperature controller.

    Parameters
    ----------
    name='auber_syl53x2p' : str
        Unique name to give this instance, so that its settings will not
        collide with other egg objects.

    show=True : bool
        Whether to show the window after creating.

    block=False : bool
        Whether to block the console when showing the window.

    window_size=[1,1] : list
        Dimensions of the window.

    """
    def __init__(self, name='auber_syl53x2p', show=True, block=False, window_size=[1,300]):
        if not _mp._minimalmodbus or not _mp._serial: _s._warn('You need to install pyserial and minimalmodbus to use the Auber SYL-53X2P.')

        # Run the base class stuff, which shows the window at the end.
        _serial_tools.serial_gui_base.__init__(self, api_class=auber_syl53x2p_api, name=name, show=False, window_size=window_size)

        self.window.set_size([0,0])

        style_big_blue = 'font-size: 20pt; font-weight: bold; color: '+('cyan' if _s.settings['dark_theme_qt'] else 'blue')
        style_big_red  = 'font-size: 20pt; font-weight: bold; color: '+('pink' if _s.settings['dark_theme_qt'] else 'red')
        style_big      = 'font-size: 20pt; font-weight: bold; color: '+('yellow' if _s.settings['dark_theme_qt'] else 'purple')

        # Add GUI stuff to the bottom grid
        self.grid_bot.add(_g.Label('Setpoint:'), alignment=2).set_style(style_big_blue)

        self.number_setpoint = self.grid_bot.add(_g.NumberBox(
            -273.16, bounds=(-273.16, 500), suffix='°C',
            signal_changed=self._number_setpoint_changed
            )).set_width(200).set_style(style_big_blue)
        self.label_temperature_status = self.grid_bot.add(_g.Label(
            '(unknown)'), row_span=2).set_style(style_big)

        self.grid_bot.new_autorow()
        self.grid_bot.add(_g.Label('Measured:'), alignment=2).set_style(style_big_red)
        
        self.number_temperature = self.grid_bot.add(_g.NumberBox(
            value=-273.16, suffix='°C', tip='Last recorded temperature value.'
            )).set_width(200).disable().set_style(style_big_red)
        
        
        self.grid_bot.new_autorow()

        # Make the plotter.
        self.grid_bot.new_autorow()
        self.plot = self.grid_bot.add(_g.DataboxPlot(
            file_type='*.csv',
            autosettings_path=name+'.plot',
            delimiter=',', show_logger=True), alignment=0, column_span=10)

        # Timer for collecting data
        self.timer = _g.Timer(interval_ms=1000, single_shot=False)
        self.timer.signal_tick.connect(self._timer_tick)

        # Bottom log file controls
        self.grid_bot.new_autorow()

        # Finally show it.
        self.window.show(block)

    def _number_setpoint_changed(self, *a):
        """
        Called when someone changes the number.
        """
        # Set the temperature setpoint
        self.api.set_temperature_setpoint(self.number_setpoint.get_value())




    def _timer_tick(self, *a):
        """
        Called whenever the timer ticks. Let's update the plot and save the latest data.
        """
        # Get the time, temperature, and setpoint
        t = _time.time()-self.t0
        T = self.api.get_temperature()
        S = self.api.get_temperature_setpoint()
        P = self.api.get_main_output_power()
        self.number_setpoint.set_value(S, block_signals=True)

        # Append this to the databox
        self.plot.append_row([t, T, S, P], ckeys=['Time (s)', 'Temperature (C)', 'Setpoint (C)', 'Power (%)'])
        self.plot.plot()

        # Update the big red text.
        self.number_temperature(T)
        self.label_temperature_status.set_text('')
        self.window.process_events()



    def _after_button_connect_toggled(self):
        """
        Called after the connection or disconnection routine.
        """
        if self.button_connect.is_checked():

            # Get the setpoint
            try:
                self.number_setpoint.set_value(self.api.get_temperature_setpoint(), block_signals=True)
                self.timer.start()
            except:
                self.number_setpoint.set_value(0)
                self.button_connect.set_checked(False)
                self.label_status.set_text('Could not get temperature.').set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')

        # Disconnected
        else:
            self.label_temperature_status('(disconnected)')
            self.timer.stop()


if __name__ == '__main__':
    _egg.clear_egg_settings()
    #self = _serial_gui_base(auber_syl53x2p_api)
    self = auber_syl53x2p()
    #self = auber_syl53x2p_api()