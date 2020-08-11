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

import numpy   as _n
import time    as _t
import spinmob as _s
import spinmob.egg as _egg
import mcphysics as _mp
import os      as _os
import time    as _time
_g = _egg.gui

import traceback as _traceback
_p = _traceback.print_last

_debug_enabled = False
def _debug(*a):
    if _debug_enabled:
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))


class _adalm2000_object():
    """
    Base class for higher-level apis.

    Parameters
    ----------
    api
        Instance of api returned by, e.g., m2k.getPowerSupply(). If None,
        simulation mode.
    """
    def __init__(self, api):
        self.more = api
        self.simulation_mode = api == None

class _adalm2000_analog_in(_adalm2000_object):

    def get_sample_rate(self):
        """
        Returns the current sample rate (Hz)
        """
        if self.simulation_mode: return 1e7
        else:                    return self.more.getSampleRate()

    def set_sample_rate(self, sample_rate=100e6):
        """
        Sets the sample rate in Hz.

        Parameters
        ----------
        sample_rate=100e6 : float, optional
            Sample rate in Hz.

        Returns
        -------
        Actual sample rate
        """
        if not self.simulation_mode:
            self.more.setSampleRate(sample_rate)
            return self.more.getSampleRate()
        return sample_rate

    def get_samples(self, samples=8192):
        """
        Queries the analog-to-digital converter, returning an array of voltages
        for each channel. If no channels are enabled, this enables both by
        default.

        Parameters
        ----------
        samples : integer, optional
            DESCRIPTION. The default is 8192.
            Number of samples to ask for. If you ask for more than the
            onboard memory (8192), you may run into buffering issues, limited
            by the usb transfer rate. That being said, I have been able to
            get a million points at 100 MHz sampling rate before.

        Returns
        -------
        List of voltage arrays, one for each channel, or None if there is a timeout.`
        """
        if self.simulation_mode: return (_n.random.normal(size=samples), _n.random.normal(size=samples))

        # If neither are enabled, enable them both.
        if not self.more.isChannelEnabled(0) and not self.more.isChannelEnabled(1):
            self.more.enableChannel(0, True)
            self.more.enableChannel(1, True)

        # Stop acquisition ("Destroy the buffer and stop acquisition.")
        self.more.stopAcquisition()

        # Send it back
        try:    return self.more.getSamples(int(samples))
        except: return None

    def set_range_big(self, channel1=None, channel2=None):
        """
        Set the channel ranges to "big" mode (+/-25V). Specifying None leaves
        them unchanged.

        Parameters
        ----------
        channel1 : bool, optional
            If True, sets channel 1 (index 0) to +/-25V mode. If False,
            sets it to +/-2.5V mode. The default is None.
        channel2 : TYPE, optional
            If True, sets channel 2 (index 1) to +/-25V mode. If False,
            sets it to +/-2.5V mode. The default is None.

        Returns
        -------
        self

        """
        if self.simulation_mode: return self

        if channel1 is not None:
            if channel1: self.more.setRange(_mp._libm2k.CHANNEL_1, _mp._libm2k.PLUS_MINUS_25V)
            else:        self.more.setRange(_mp._libm2k.CHANNEL_1, _mp._libm2k.PLUS_MINUS_2_5V)

        if channel2 is not None:
            if channel2: self.more.setRange(_mp._libm2k.CHANNEL_2, _mp._libm2k.PLUS_MINUS_25V)
            else:        self.more.setRange(_mp._libm2k.CHANNEL_2, _mp._libm2k.PLUS_MINUS_2_5V)

        return self

    def set_range_small(self, channel1=None, channel2=None):
        """
        Set the channel ranges to "small" mode (+/-25V). Specifying None leaves
        them unchanged.

        Parameters
        ----------
        channel1 : bool, optional
            If True, sets channel 1 (index 0) to +/-2.5V mode. If False,
            sets it to +/-25V mode. The default is None.
        channel2 : TYPE, optional
            If True, sets channel 2 (index 1) to +/-2.5V mode. If False,
            sets it to +/-25V mode. The default is None.

        Returns
        -------
        self

        """
        if channel1 is not None:
            if channel1: self.more.setRange(_mp._libm2k.CHANNEL_1, _mp._libm2k.PLUS_MINUS_2_5V)
            else:        self.more.setRange(_mp._libm2k.CHANNEL_1, _mp._libm2k.PLUS_MINUS_25V)

        if channel2 is not None:
            if channel2: self.more.setRange(_mp._libm2k.CHANNEL_2, _mp._libm2k.PLUS_MINUS_2_5V)
            else:        self.more.setRange(_mp._libm2k.CHANNEL_2, _mp._libm2k.PLUS_MINUS_25V)

        return self

    def set_trigger_modes(self, mode1, mode2):
        """
        Set the trigger mode. Trigger modes for channels 1 and 2 (mode1 and mode2)
        are integers corresponding to the following:

            0: Immediate trigger (always)
            1: Analog Condition
            2: External
            3: Digital or Analog
            4: Digital and Analog
            5: Digital xor Analog
            6: N Digital or Analog
            7: N Digital and Analog
            8: N Digital xor Analog

        Parameters
        ----------
        mode1 : int
            Trigger mode for channel 1
        mode2 : int
            Trigger mode for channel 2


        Returns
        -------
        self
        """
        if not self.simulation_mode:
            self.more.getTrigger().setAnalogMode(0,mode1)
            self.more.getTrigger().setAnalogMode(1,mode2)
        return self

    def set_trigger_in(self, source):
        """
        Sets the hardware trigger source.

        Parameters
        ----------
        source : int
            Integer value indicating the trigger source.
            0: 'Ch1',
            1: 'Ch2',
            2: 'Ch1 or Ch2',
            3: 'Ch1 and Ch2',
            4: 'Ch1 xor Ch2',
            5: 'Digital In',
            6: 'Ch1 or Logic',
            7: 'Ch2 or Logic',
            8: 'Ch1 or Ch2 or Logic'

        Returns
        -------
        self
        """
        if not self.simulation_mode: self.more.getTrigger().setAnalogSource(source)
        return self

    def set_trigger_out(self, source):
        """
        Selects which trigger event will be forwarded to the TO pin.

        Parameters
        ----------
        source : int
            Integer value indicating the trigger out terminal.
            0: 'None',
            1: 'Same Channel',
            2: 'Trigger In',
            3: 'Analog In',
            4: 'Digital In',

        Returns
        -------
        self
        """
        if not self.simulation_mode: self.more.getTrigger().setAnalogExternalOutSelect(source)
        return self

    def set_trigger_conditions(self, condition1, condition2):
        """
        Sets the trigger conditions for the two channels. Each integer
        specifier (condition1 and condition2) can take values from 0 to 3, with this meaning:
            0: Rising edge
            1: Falling edge
            2: Low level
            3: High level

        Parameters
        ----------
        condition1 : int
            Integer specifying the trigger condition for channel 1.
        condition2 : int
            Integer specifying the trigger condition for channel 2.

        Returns
        -------
        self

        """
        if not self.simulation_mode:
            t = self.more.getTrigger()
            t.setAnalogCondition(0, condition1)
            t.setAnalogCondition(1, condition2)

        return self

    def get_trigger_levels(self):
        """
        Returns the trigger levels (Volts) in a tuple.
        """
        if self.simulation_mode: return 0,0
        else:
            t = self.more.getTrigger()
            return t.getAnalogLevel(0), t.getAnalogLevel(1)


    def set_trigger_levels(self, V1, V2):
        """
        Sets the trigger levels for the two channels.

        Parameters
        ----------
        V1 : float
            Trigger voltage level for channel 1
        V2 : float
            Trigger voltage level for channel 2

        Returns
        -------
        self

        """
        if not self.simulation_mode:
            t = self.more.getTrigger()
            t.setAnalogLevel(0, V1)
            t.setAnalogLevel(1, V2)

        return self

    def set_trigger_hystereses(self, V1, V2):
        """
        Set the voltage hysteresis for the two channels.

        Parameters
        ----------
        V1 : float
            Voltage hysteresis for channel 1's trigger.
        V2 : float
            Voltage hysteresis for channel 2's trigger.

        Returns
        -------
        self
        """
        if not self.simulation_mode:
            t = self.more.getTrigger()
            t.setAnalogHysteresis(0, V1)
            t.setAnalogHysteresis(1, V2)
        return self

    def get_trigger_delay(self):
        """
        Returns the trigger delay in seconds.
        """

        if not self.simulation_mode:
            t = self.more.getTrigger()
            return t.getAnalogDelay() / self.get_sample_rate()
        return 0

    def set_trigger_delay(self, delay=0.0):
        """
        Sets the trigger delay in seconds.

        Parameters
        ----------
        delay : float
            Trigger delay in seconds.

        Returns
        -------
        Actual trigger delay in seconds (self.get_trigger_delay()).
        """
        if not self.simulation_mode:
            t = self.more.getTrigger()

            # Convert to samples and limit at -8192
            N = int(delay*self.get_sample_rate())
            if N < -8192: N = -8192

            # Set it and check it.
            t.setAnalogDelay(N)
            return self.get_trigger_delay()
        return delay

class _adalm2000_analog_out(_adalm2000_object):

    def get_sample_rates(self):
        """
        Returns the sample rates for each channel as tuple.
        """
        if not self.simulation_mode: return self.more.getSampleRate(0), self.more.getSampleRate(1)
        else: return 100.0, 100.0

    def set_sample_rates(self, sample_rate1, sample_rate2):
        """
        Sets the analog out sample rate.

        Parameters
        ----------
        sample_rate1 : float
            Rate (Hz) for analog out 1.
        sample_rate2 : float
            Rate (Hz) for analog out 2.

        Returns
        -------
        Actual sample rate
        """
        if not self.simulation_mode:
            self.more.setSampleRate(0, sample_rate1)
            self.more.setSampleRate(1, sample_rate2)
        return self.get_sample_rates()

    def get_enabled(self):
        """
        Returns the enabled state of each channel.
        """
        if self.simulation_mode: return True, True
        return self.more.isChannelEnabled(0), self.more.isChannelEnabled(1)

    def set_enabled(self, enable1, enable2):
        """
        Sets which channels are enabled.

        Parameters
        ----------
        enable1 : bool
            Whether channel 1 is enabled.
        enable2 : bool
            Whether channel 2 is enabled.

        Returns
        -------
        The enabled states (self.get_enabled())
        """
        if not self.simulation_mode:
            self.more.enableChannel(0, enable1)
            self.more.enableChannel(1, enable2)
        return self.get_enabled()

    enable = set_enabled

    def get_loop_modes(self):
        """
        Returns the loop mode of both channels as tuple.
        """
        if self.simulation_mode: return True, True
        return self.more.getCyclic(0), self.more.getCyclic(1)

    def set_loop_modes(self, loop1, loop2):
        """
        Sets the loop mode for each channel.

        Parameters
        ----------
        loop1 : bool
            Whether channel 1 is loop.
        loop2 : bool
            Whether channel 2 is loop.

        Returns
        -------
        The loop state of each.
        """
        if not self.simulation_mode:
            # This is a hack that made it work reliably.
            # Without messing with the buffer, it would only do
            # one at a time.
            self.zero()
            self.more.setCyclic(0, loop1)
            self.more.setCyclic(1, loop2)
            self.zero()
            self.more.setCyclic(0, loop1)
            self.more.setCyclic(1, loop2)

        return self.get_loop_modes()

    def send_samples(self, channel, samples):
        """
        Sends the samples to a given output channel.

        Parameters
        ----------
        channel : int
            Output channel number (1 or 2) to send the samples to.
        samples : 1D array
            Voltages for this output channel.

        Returns
        -------
        self
        """
        if not self.simulation_mode:
            if not channel in [1,2]:
                print('WARNING: send_samples() requires channel == 1 or 2')
                channel = 1 # Some dummy proofing
            self.more.push(channel-1, samples)
        return self

    def send_samples_dual(self, V1, V2):
        """
        Streams the supplied two voltage arrays in parallel (synchronized)
        to the two outputs.

        Parameters
        ----------
        V1 : array of floats
            Voltages to stream to analog output 1.
        V2 : array of floats
            Voltages to stream to analog output 2.

        Returns
        -------
        self
        """
        if not self.simulation_mode: self.more.push([V1, V2])
        return self

    def zero(self):
        """
        Zero it. Stopping gives strange results. Disabling doesn't have an effect.
        """
        if not self.simulation_mode:
            self.set_enabled(True, True)
            self.send_samples_dual(_n.zeros(1), _n.zeros(1))

class _adalm2000_power(_adalm2000_object):

    def get_Vp(self):
        """
        Returns the current value of V+ on the power supply.
        """
        if self.simulation_mode: return _n.random.rand()-0.5
        return self.more.readChannel(0)

    def get_Vm(self):
        """
        Returns the current value of V- on the power supply.
        """
        if self.simulation_mode: return _n.random.rand()-0.5
        else:                    return self.more.readChannel(1)

    def set_Vp(self, Vp):
        """
        Sets V+.
        """
        if not self.simulation_mode:
            self.more.enableChannel(0, True)
            self.more.pushChannel  (0, Vp)
        return self

    def set_Vm(self, Vm):
        """
        Sets V-.
        """
        if not self.simulation_mode:
            self.more.enableChannel(1, True)
            self.more.pushChannel  (1, Vm)
        return self

class adalm2000_api():
    """
    Class for talking to an ADALM2000.

    Parameters
    ----------
    name : str
        Short name ('uri') of the device to open, e.g., 'usb:2.11.5'.
    """
    def __init__(self, name):

        # If the import failed, _mp._libm2k = None
        if _mp._libm2k == None:
            _s._warn('You need to install libm2k to access the adalm2000s.')
            self.simulation_mode = True
            self.ai    = _adalm2000_analog_in(None)
            self.ao    = _adalm2000_analog_out(None)
            self.power = _adalm2000_power(None)

        # Assume it's working.
        else:
            # Open the connection
            print('Opening "'+name+'"')

            # If we are trying to open a real object
            if not name == "Simulation":

                # Create the m2k handle
                self.m2k = _mp._libm2k.contextOpen(name).toM2k()

                # Get the ai, ao, and power.
                self.ai    = _adalm2000_analog_in (self.m2k.getAnalogIn())
                self.ao    = _adalm2000_analog_out(self.m2k.getAnalogOut())
                self.power = _adalm2000_power     (self.m2k.getPowerSupply())

                # Run the calibration
                print('Calibrating...')
                self.m2k.calibrate()

                # Not simulation mode
                self.simulation_mode = False

            # If anything goes wrong, simulation mode
            else:
                self.ai    = _adalm2000_analog_in(None)   # Simulated ai
                self.ao    = _adalm2000_analog_out(None)  # Simulated ao
                self.power = _adalm2000_power(None) # Simulated power supply
                self.simulation_mode = True

    def get_infostring(self):
        """
        Returns an info string for this device.
        """
        return 'ADALM2000 Firmware '+self.m2k.getFirmwareVersion()+', S/N '+self.m2k.getSerialNumber() + ' <-- Memorize this.'

    def set_timeout(self, timeout_ms):
        """
        Set's the timeout for input/output operations.

        Parameters
        ----------
        timeout_ms : int
            Integer number of milliseconds before it gives up.

        Returns
        -------
        self
        """
        if not self.simulation_mode: self.m2k.setTimeout(timeout_ms)
        return self

class adalm2000():
    """
    Graphical interface for an ADALM2000.

    Parameters
    ----------
    name : str, optional
        Optional identifier for this instance of adalm2000 (in case you build
        a gui with many instances), used primarily for the remembering settings.
        Could be "Carl" for example.
    """
    def __init__(self, name='adalm2000', block=False):

        if _mp._libm2k == None: _s._warn('You need to install libm2k to access the adalm2000s.')

        # Remember the name
        self.name = name

        # Build the graphical user interface
        self._build_gui(block)


    def _build_gui(self, block=False):
        """
        Builds the graphical interface
        """
        # Create the window
        w = self.window = _g.Window('ADALM2000', autosettings_path=self.name+'.window', size=[1325,10])

        # Top row for connection interface, bottom row for data taking
        gt = self._grid_top    = w.add(_g.GridLayout(margins=False), column=1, row=1, alignment=0)
        gb = self._grid_bottom = w.add(_g.GridLayout(margins=False), column=1, row=2, alignment=0)

        # Add a combo box for all the available devices and a button to connect
        if _mp._libm2k: contexts = list(_mp._libm2k.getAllContexts())
        else:    contexts = []
        contexts.append('Simulation')
        self.combo_contexts = gt.add(_g.ComboBox(contexts, tip='Choose a device.'))
        self.button_connect = gt.add(_g.Button('Connect', checkable=True, tip='Connect to chosen device.'))
        self.label_status   = gt.add(_g.Label(''))
        gt.set_column_stretch(2)

        # Add tabs for the different devices on the adalm2000
        self.tabs = gb.add(_g.TabArea(self.name+'.tabs'), alignment=0)

        # Add the tabs for the different functionalities
        self._build_tab_ai()
        self._build_tab_ao()
        self._build_tab_li()
        self._build_tab_power()

        # Connect remaining signals
        self.button_connect.signal_clicked.connect(self._button_connect_clicked)

        # Disable the tabs until we connect
        self.tabs.disable()

        # Let's see it!
        self.window.show(block)


    def _build_tab_power(self):
        """
        Populates the power tab.
        """
        # Power tab
        self.tab_power = self.tabs.add_tab('Power Supply')
        self.tab_power.number_set_Vp    = self.tab_power.add(_g.NumberBox(5, 1, (0,5), suffix='V', siPrefix=True, tip='Setpoint for the positive supply.'))
        self.tab_power.button_enable_Vp = self.tab_power.add(_g.Button('Enable V+', checkable=True, tip='Enable the positive supply.'))
        self.tab_power.button_monitor_Vp= self.tab_power.add(_g.Button('Monitor',   checkable=True, checked=True, tip='Monitor the actual output voltage.'))
        self.tab_power.label_Vp         = self.tab_power.add(_g.Label(''))

        self.tab_power.new_autorow()
        self.tab_power.number_set_Vm    = self.tab_power.add(_g.NumberBox(-5, 1, (-5,0), suffix='V', siPrefix=True, tip='Setpoint for the negative supply.'))
        self.tab_power.button_enable_Vm = self.tab_power.add(_g.Button('Enable V-', checkable=True, tip='Enable the negative supply.'))
        self.tab_power.button_monitor_Vm= self.tab_power.add(_g.Button('Monitor',   checkable=True, checked=True, tip='Monitor the actual output voltage.'))
        self.tab_power.label_Vm         = self.tab_power.add(_g.Label(''))

        self.tab_power.new_autorow()
        self.tab_power.plot = self.tab_power.add(_g.DataboxPlot("*.txt", autosettings_path=self.name+'.tab_power.plot'), alignment=0, column_span=4)

        # Formatting
        self.tab_power.set_column_stretch(3)
        self.tab_power.set_row_stretch(2)

        # Connect all the signals
        self.tab_power.number_set_Vp     .signal_changed.connect(self._power_settings_changed)
        self.tab_power.number_set_Vm     .signal_changed.connect(self._power_settings_changed)
        self.tab_power.button_enable_Vp  .signal_clicked.connect(self._power_settings_changed)
        self.tab_power.button_enable_Vm  .signal_clicked.connect(self._power_settings_changed)

        # Timer for power update
        self.tab_power.timer = _g.Timer(500)
        self.tab_power.timer.signal_tick.connect(self._power_timer_tick)

    def _build_tab_ai(self):
        """
        Builds the innards of the analog in tab.
        """
        self._ai_rates = [100e6, 100e5, 100e4, 100e3, 100e2, 100e1]

        # ADC Tab
        self.tab_ai = self.tabs.add_tab('Analog In')

        # Tab area for settings
        self.tab_ai.tabs_settings = self.tab_ai.add(_g.TabArea(autosettings_path=self.name+'.tab_ai.tabs_settings'))
        self.tab_ai.tab_controls  = self.tab_ai.tabs_settings.add_tab('AI Settings')

        self.tab_ai.button_acquire = self.tab_ai.tab_controls.add(_g.Button('Acquire', checkable=True, tip='Acquire voltages vs time according to the settings below.'))
        self.tab_ai.button_onair   = self.tab_ai.tab_controls.add(_g.Button('On Air',  checkable=True, tip='Indicates when data is actually being collected.')).set_width(50)
        self.tab_ai.label_info     = self.tab_ai.tab_controls.add(_g.Label(''))

        # Add sub-tabs for ai plot & analysis
        self.tab_ai.tabs_data     = self.tab_ai.add(_g.TabArea(autosettings_path=self.name+'.tabs_data'), alignment=0)

        self.tab_ai.tab_raw  = self.tab_ai.tabs_data.add_tab('AI Raw Voltages')
        self.tab_ai.plot_raw = self.tab_ai.tab_raw.add(_g.DataboxPlot('*.ai', autosettings_path=self.name+'.tab_ai.plot_raw'), alignment=0)
        self.tab_ai.plot_raw.ROIs = [
            [_egg.pyqtgraph.InfiniteLine(angle=90, movable=True, pen=(0,2)),
             _egg.pyqtgraph.InfiniteLine(angle=0,  movable=True, pen=(0,2))],
            [_egg.pyqtgraph.InfiniteLine(angle=90, movable=True, pen=(1,2)),
             _egg.pyqtgraph.InfiniteLine(angle=0,  movable=True, pen=(1,2))]]

        # Some initial data so the ROIs appear
        self.tab_ai.plot_raw['t'] = [0]
        self.tab_ai.plot_raw['V1'] = [0]
        self.tab_ai.plot_raw['V2'] = [0]
        self.tab_ai.plot_raw.plot()

        ### Processor tab

        # Add additional analysis tabs
        self.tab_ai.tab_A1 = self.tab_ai.tabs_data.add_tab('A1')
        self.tab_ai.A1     = self.tab_ai.tab_A1.add(_g.DataboxProcessor('A1', self.tab_ai.plot_raw, '*.A1'), alignment=0)
        self.tab_ai.tab_A2 = self.tab_ai.tabs_data.add_tab('A2')
        self.tab_ai.A2     = self.tab_ai.tab_A2.add(_g.DataboxProcessor('A2', self.tab_ai.A1.plot,  '*.A2'), alignment=0)
        self.tab_ai.tab_A3 = self.tab_ai.tabs_data.add_tab('A3')
        self.tab_ai.A3     = self.tab_ai.tab_A3.add(_g.DataboxProcessor('A3', self.tab_ai.A2.plot,  '*.A3'), alignment=0)

        self.tab_ai.tab_B1 = self.tab_ai.tabs_data.add_tab('B1')
        self.tab_ai.B1     = self.tab_ai.tab_B1.add(_g.DataboxProcessor('B1', self.tab_ai.plot_raw, '*.B1'), alignment=0)
        self.tab_ai.tab_B2 = self.tab_ai.tabs_data.add_tab('B2')
        self.tab_ai.B2     = self.tab_ai.tab_B2.add(_g.DataboxProcessor('B2', self.tab_ai.B1.plot,  '*.B2'), alignment=0)
        self.tab_ai.tab_B3 = self.tab_ai.tabs_data.add_tab('B3')
        self.tab_ai.B3     = self.tab_ai.tab_B3.add(_g.DataboxProcessor('B3', self.tab_ai.B2.plot,  '*.B3'), alignment=0); self._libregexdisp_ctl()

        # After loading a raw file, run the processors
        self.tab_ai.plot_raw.after_load_file = self.after_load_ai_plot_raw

        # Settings for the acquisition
        self.tab_ai.tab_controls.new_autorow()
        s = self.tab_ai.settings  = self.tab_ai.tab_controls.add(_g.TreeDictionary(self.name+'.tab_ai.settings', name='AI'), column_span=4)
        s.add_parameter('Iterations', 0, tip='How many acquisitions to perform.')
        s.add_parameter('Samples', 1000, bounds=(2,None), siPrefix=True, suffix='S', dec=True, tip='How many samples to acquire. 1-8192 guaranteed. \nLarger values possible, depending on USB bandwidth.')
        s.add_parameter('Rate', ['100 MHz', '10 MHz', '1 MHz', '100 kHz', '10 kHz', '1 kHz'], tip='How fast to sample voltages.')
        s.add_parameter('Timeout', 0.2, bounds=(0.1,None), suffix='s', siPrefix=True, dec=True, tip='How long to wait for a trigger before giving up. 0 means "forever"; be careful with that setting ;).')
        s.add_parameter('Timeout/Then_What', ['Immediate', 'Wait Again', 'Quit'], bounds=(0,None), suffix='s', siPrefix=True, dec=True, tip='How long to wait for a trigger before giving up. 0 means "forever"; be careful with that setting ;).')

        # This does not have an effect for some reason, so I disabled it.
        # I notice one cannot disable channels in Scopy either.
        #s.add_parameter('Ch1', True, tip='Enable Channel 1')
        #s.add_parameter('Ch2', True, tip='Enable Channel 2')

        s.add_parameter('Ch1_Range', ['25V', '2.5V'], tip='Range of accepted voltages.')
        s.add_parameter('Ch2_Range', ['25V', '2.5V'], tip='Range of accepted voltages.')


        # Note these lists MUST be in this order; their indices are
        # constants defined by libm2k: https://analogdevicesinc.github.io/libm2k/enums_8hpp.html

        s.add_parameter('Trigger/In', [
            'Ch1',
            'Ch2',
            'Ch1 or Ch2',
            'Ch1 and Ch2',
            'Ch1 xor Ch2',
            'Digital In',
            'Ch1 or Logic',
            'Ch2 or Logic',
            'Ch1 or Ch2 or Logic'
            ], tip='Which source to use for triggering an acquisition.')

        s.add_parameter('Trigger/Out', [
            'None',
            'Same Channel',
            'Trigger In',
            'Analog In',
            'Digital In'
            ], tip='Which source to use for triggering an acquisition.')

        s.add_parameter('Trigger/Delay', 0.0, suffix='s', siPrefix=True, step=0.01,
                        tip='Horizontal (time) offset relative to trigger point. The trigger point is always defined to be at time t=0.')

        s.add_parameter('Trigger/Ch1', [
            'Immediate',
            'Analog',
            'External',
            'Digital or Analog',
            'Digital and Analog',
            'Digital xor Analog',
            'N Digital or Analog',
            'N Digital and Analog',
            'N Digital xor Analog'
            ], tip='Trigger mode.')

        s.add_parameter('Trigger/Ch2', [
            'Immediate',
            'Analog',
            'External',
            'Digital or Analog',
            'Digital and Analog',
            'Digital xor Analog',
            'N Digital or Analog',
            'N Digital and Analog',
            'N Digital xor Analog'
            ], tip='Trigger mode.')

        s.add_parameter('Trigger/Ch1/Condition', ['Rising', 'Falling', 'Low Level', 'High Level'], tip='Type of trigger for this channel')
        s.add_parameter('Trigger/Ch2/Condition', ['Rising', 'Falling', 'Low Level', 'High Level'], tip='Type of trigger for this channel')

        s.add_parameter('Trigger/Ch1/Level', 0.0, step=0.01, suffix='V', siPrefix=True, tip='Trigger level (Volts).')
        s.add_parameter('Trigger/Ch2/Level', 0.0, step=0.01, suffix='V', siPrefix=True, tip='Trigger level (Volts).')

        s.add_parameter('Trigger/Ch1/Hysteresis', 0.0, bounds=(0, 2.5), dec=True, suffix='V', siPrefix=True, tip='How far the signal must swing away from the trigger level before another trigger is accepted.')
        s.add_parameter('Trigger/Ch2/Hysteresis', 0.0, bounds=(0, 2.5), dec=True, suffix='V', siPrefix=True, tip='How far the signal must swing away from the trigger level before another trigger is accepted.')

        self.tab_ai.button_auto = s.add_button('Trigger/Auto', tip="Select reasonable trigger levels based on the currently shown data.")

        # Formatting
        self.tab_ai.set_column_stretch(1, 10)

        # Transfer settings to plots etc
        self._ai_settings_changed()

        # Connect all the signals.
        self.tab_ai.button_acquire.signal_clicked.connect(self._ai_button_acquire_clicked)
        self.tab_ai.settings.connect_signal_changed('Trigger/Ch1/Level', self._ai_settings_changed)
        self.tab_ai.settings.connect_signal_changed('Trigger/Ch2/Level', self._ai_settings_changed)
        self.tab_ai.settings.connect_signal_changed('Trigger/Delay', self._ai_settings_changed)
        self.tab_ai.button_auto.signal_clicked.connect(self._ai_button_auto_clicked)

        # Trigger cursors
        self.tab_ai.plot_raw.ROIs[0][0].sigPositionChanged.connect(self._ai_cursor_drag)
        self.tab_ai.plot_raw.ROIs[1][0].sigPositionChanged.connect(self._ai_cursor_drag)
        self.tab_ai.plot_raw.ROIs[0][1].sigPositionChanged.connect(self._ai_cursor_drag)
        self.tab_ai.plot_raw.ROIs[1][1].sigPositionChanged.connect(self._ai_cursor_drag)

    def _build_tab_ao(self):
        """
        Assembles the analog out tab.
        """
        self._ao_rates = [75e6, 75e5, 75e4, 75e3, 75e2, 75e1]

        # DAC Tab
        self.tab_ao =self.tabs.add_tab('Analog Out')

        # Settings tabs
        self.tab_ao.tabs_settings = self.tab_ao.add(_g.TabArea(autosettings_path=self.name+'.tab_ao.tabs_settings'))
        self.tab_ao.tab_controls  = self.tab_ao.tabs_settings.add_tab('AO Settings')

        self.tab_ao.button_send   = self.tab_ao.tab_controls.add(_g.Button('Send', checkable=True, tip='Send the designed waveform to the actual analog outputs.'))
        self.tab_ao.checkbox_auto = self.tab_ao.tab_controls.add(_g.CheckBox('Auto', autosettings_path=self.name+'.tab_ao.checkbox_auto', tip='Automatically send the designed waveform whenever it changes.'))
        self.tab_ao.button_stop   = self.tab_ao.tab_controls.add(_g.Button('Stop', tip='Stop the output and set it to zero.'))

        # Waveform inspector
        self.tab_ao.tabs_data   = self.tab_ao.add(_g.TabArea(autosettings_path=self.name+'.tab_ao.tabs_data'), alignment=0)
        self.tab_ao.tab_design  = self.tab_ao.tabs_data.add_tab('AO Waveform Designer')
        self.tab_ao.tab_sent    = self.tab_ao.tabs_data.add_tab('AO Last Sent Waveform')
        self.tab_ao.plot_design = p = self.tab_ao.tab_design.add(_g.DataboxPlot('*.ao', autosettings_path=self.name+'.tab_ao.plot_design', autoscript=2), alignment=0)
        self.tab_ao.plot_sent       = self.tab_ao.tab_sent  .add(_g.DataboxPlot('*.ao', autosettings_path=self.name+'.tab_ao.plot_sent',   autoscript=2), alignment=0)

        # Default column positions
        p['t1'] = []
        p['V1'] = []
        p['t2'] = []
        p['V2'] = []

        # Settings
        self.tab_ao.tab_controls.new_autorow()
        self.tab_ao.settings = self.tab_ao.tab_controls.add(_g.TreeDictionary(autosettings_path=self.name+'.tab_ao.settings', name='AO'), column_span=3)
        self._ao_settings_add_channel('Ch1')
        self._ao_settings_add_channel('Ch2')

        # Update design
        self._ao_settings_changed()

        # Link callbacks
        self.tab_ao.checkbox_auto.signal_toggled.connect (self._ao_settings_changed)
        self.tab_ao.settings.connect_any_signal_changed(self._ao_settings_changed)
        self.tab_ao.button_send.signal_clicked.connect(self._ao_button_send_clicked)
        self.tab_ao.button_stop.signal_clicked.connect(self._ao_button_stop_clicked)

        # Other stuff
        self.tab_ao.plot_design.after_load_file = self._ao_after_plot_design_load

        # Formatting
        self.tab_ao.set_column_stretch(1)

    def _build_tab_li(self):
        """
        Populates the lockin tab.
        """
        self.tab_li = tl = self.tabs.add_tab('Lock-In')

        # Settings Tab
        tl.tabs_settings     = tl.add(_g.TabArea(self.name+'.tab_li.tabs_settings'))
        tl.tab_settings = ts = tl.tabs_settings.add_tab('LI Settings')
        tl.number_ao_frequency = ts.add(_g.NumberBox(1e5, suffix='Hz', siPrefix=True, dec=True, bounds=(0, None), autosettings_path=self.name+'.tab_li.number_ao_frequency', tip='Target output frequency.')).set_width(80)
        tl.label_samples     = ts.add(_g.Label(''))
        ts.new_autorow()
        tl.button_go         = ts.add(_g.Button('Go!',   checkable=True, tip='Set the frequency, acquire data, and demodulate it.'))
        tl.button_sweep      = ts.add(_g.Button('Sweep', checkable=True, tip='Step the frequency according to the sweep below, pressing the "Go!" button at each step.'))
        ts.new_autorow()
        tl.settings     = s  = ts.add(_g.TreeDictionary(self.name+'.tab_li.tab_settings.settings', name='LI'), column_span=4)
        ts.set_column_stretch(3)

        # Data Tab
        tl.tabs_data              = tl.add(_g.TabArea(self.name+'.tab_li.tabs_data'), alignment=0)
        tl.tab_plot   = tp        = tl.tabs_data.add_tab('LI Demodulation')
        tl.number_demod_frequency = tp.add(_g.NumberBox(0.0, suffix='Hz', siPrefix=True, autosettings_path=self.name+'.tab_li.number_demod_frequency', tip='Frequency at which to perform the demodulation. Can be different from the LI settings frequency.')).set_width(120)
        tl.checkbox_enable        = tp.add(_g.CheckBox('Enable Demodulation', autosettings_path=self.name+'.tab_li.checkbox_enable', tip='Demodulate the next incoming data at the frequency to the left, and append the result.'))
        tp.new_autorow()
        tl.plot             = tp.add(_g.DataboxPlot('*.lockin', self.name+'.tab_li.plot'), column_span=4, alignment=0)
        tp.set_column_stretch(3)

        # Lock-in settings
        s.add_parameter('Iterations',  1, bounds=(0,None), tip='How many iterations to take at each frequency.')
        s.add_parameter('Output/Rate', ['75 MHz', '7.5 MHz', '750 kHz', '75 kHz', '7.5 kHz', '750 Hz', 'Automatic'], default_list_index=6, tip='Analog output sampling rate for both channels.')
        s.add_parameter('Output/Min_Buffer', 200, bounds=(10,None), dec=True, tip='Minimum samples you want the waveform to contain. As of libm2k v0.2.1, keep this above 200 or there is a serious jitter issue.')
        s.add_parameter('Output/Max_Buffer',8192, bounds=(10,None), dec=True, tip='Maximum samples you want the waveform to contain. Increase this to increase frequency resolution, at the expense of slower sends and eventual buffer crash.')
        s.add_parameter('Output/Amplitude', 0.1, suffix='V', siPrefix=True, dec=True, tip='Amplitude of output sinusoid.')
        s.add_parameter('Output/Trigger_Out', ['Ch1', 'Ch2'], default_list_index=1, tip='Which channel to use as the trigger output. You can set the square wave attributes in the Analog Out tab.')

        s.add_parameter('Input/Rate', ['100 MHz', '10 MHz', '1 MHz', '100 kHz', '10 kHz', '1 kHz', 'Automatic'], default_list_index=6, tip='Analog input samping rate for both channels.')
        s.add_parameter('Input/Max_Buffer',100000, bounds=(10,None), dec=True, tip='Maximum input buffer you will tolerate to try and achieve Tau.')
        s.add_parameter('Input/Settle',  50e-6, suffix='s', siPrefix=True, dec=True, bounds=(0,   None), tip='How long to let it settle after starting the analog output before acquiring.')
        s.add_parameter('Input/Trigger_In', ['Ch1', 'Ch2', 'External'], default_list_index=1, tip='Which channel to use as a trigger. "External" refers to the TI port.')
        s.add_parameter('Input/Measure', 50e-6, suffix='s', siPrefix=True, dec=True, bounds=(1e-6,None), tip='How long to take data. This will be limited by Max_Buffer.')

        s.add_parameter('Sweep/Start',  1e4, suffix='Hz', siPrefix=True, dec=True, bounds=(0,None), tip='Approximate start frequency. Be careful with low frequencies and high sample rates. Too many samples will crash this thing.')
        s.add_parameter('Sweep/Stop',   1e6, suffix='Hz', siPrefix=True, dec=True, bounds=(0,None), tip='Approximate start frequency. Be careful with low frequencies and high sample rates. Too many samples will crash this thing.')
        s.add_parameter('Sweep/Steps',  100, dec=True, bounds=(2,None), tip='How many steps to take between f1 and f2')
        s.add_parameter('Sweep/Log_Scale',         False, tip='Log frequency steps?')
        s.add_parameter('Sweep/Auto_Script', False, tip='Whether to load the "appropriate" script into the plotter.')

        # Link signals to functions
        tl.button_go.signal_clicked          .connect(self._li_button_go_clicked)
        tl.button_sweep.signal_clicked       .connect(self._li_button_sweep_clicked)

        tl.number_ao_frequency.signal_changed.connect(self._li_settings_changed)
        s.connect_any_signal_changed                 (self._li_settings_changed)

        self._li_settings_changed()

    def demodulate(self, f=None):
        """
        Perform a demodulation of both Analog input channels at the specified
        frequency f.

        Parameters
        ----------
        f=None : float
            Frequency at which to perform the demodulation. If f=None, this will
            use the current value in self.tab_li.number_demod_frequency.

        Returns
        -------
        self
        """
        # Get or set the demod frequency.
        if f==None: f = self.tab_li.number_demod_frequency.get_value()
        else:           self.tab_li.number_demod_frequency.set_value(f)

        # Get the source databox and demod plotter
        d = self.tab_ai.plot_raw
        p = self.tab_li.plot

        # Get the time axis and the two quadratures
        t = d[0]
        X = _n.cos(2*_n.pi*f*t)
        Y = _n.sin(2*_n.pi*f*t)

        # Normalize
        X = _n.nan_to_num(X/sum(X*X))
        Y = _n.nan_to_num(Y/sum(Y*Y))

        # Demodulate
        V1X = sum(d['V1']*X)
        V1Y = sum(d['V1']*Y)
        V2X = sum(d['V2']*X)
        V2Y = sum(d['V2']*Y)

        # Get the next index
        if not len(p): n = 0
        else:          n = len(p[0])

        # Append to the demodder
        p.append_row([n, f, V1X, V1Y, V2X, V2Y], ['n', 'f', 'V1X', 'V1Y', 'V2X', 'V2Y'])

        # Update the header
        d.copy_headers_to(p)
        self.tab_ao.settings.send_to_databox_header(p)
        self.tab_li.settings.send_to_databox_header(p)

        # Plot!
        p.plot()

    def _li_button_go_clicked(self, *a):
        """
        Take single demodulations for the specified iterations, without stepping frequency.
        Appends them to the LI Demodulation plot.
        """
        # If we just turned it off, poop out instead of starting another loop.
        if not self.tab_li.button_go.is_checked(): return

        # Reset the button colors (they turn red when it's not locked / triggered)
        self.tab_li.button_go.set_colors(None, None)

        # Enable demodulation analysis
        self.tab_li.checkbox_enable.set_checked(True)

        # Make sure the first iteration gets set correctly
        self._li_needs_configure_ao_ai = True

        # Now start the single-frequency loop!
        n=0
        while (n < self.tab_li.settings['Iterations'] or self.tab_li.settings['Iterations'] <= 0) \
        and self.tab_li.button_go.is_checked():

            # Reconfigure
            self._li_configure_ao_ai() # This is just GUI updates; it resets the trigger if it failed, e.g.
            if self._li_needs_configure_ao_ai:

                # Reset the flag and send the analog out data at the same time
                # If someone changes the frequency it will trigger a redo
                self._li_needs_configure_ao_ai = False
                self.tab_ao.button_send.click()

                # Wait for the send to finish
                while self.tab_ao.button_send.is_checked(): self.window.sleep(0.01)

                # Settle
                self.window.sleep(self.tab_li.settings['Input/Settle'])

            # Acquire
            self.tab_ai.button_acquire.click()

            # Wait for this to complete
            while self.tab_ai.button_acquire.is_checked(): self.window.sleep()

            # Increment and display
            n += 1

            # Update GUI
            self.window.process_events()

        # All done!
        self.tab_li.button_go    .set_checked(False)
        self.tab_li.checkbox_enable.set_checked(False)



    def _li_button_sweep_clicked(self, *a):
        """
        Starts a sweep.
        """
        # If we just unchecked it, let the loop poop itself out.
        if not self.tab_li.button_sweep.is_checked(): return
        s = self.tab_li.settings

        # If iterations is zero, set it to 1 to prevent an infinite loop
        if s['Iterations'] < 1: s['Iterations'] = 1

        # Clear the plot
        self.tab_li.plot.clear()

        # Load the plot script if we're supposed to
        if s['Sweep/Auto_Script']:

            if s['Sweep/Log_Scale']: self.tab_li.plot.load_script(_os.path.join(_mp.__path__[0], 'plot_scripts', 'ADALM2000', 'li_sweep_magphase_log.py'))
            else:              self.tab_li.plot.load_script(_os.path.join(_mp.__path__[0], 'plot_scripts', 'ADALM2000', 'li_sweep_magphase.py'))

        # Get the frequency list
        if s['Sweep/Log_Scale']: fs = _s.fun.erange(s['Sweep/Start'], s['Sweep/Stop'], s['Sweep/Steps'])
        else:              fs = _n.linspace  (s['Sweep/Start'], s['Sweep/Stop'], s['Sweep/Steps'])

        # Do the loop
        for f in fs:

            # If we've aborted
            if not self.tab_li.button_sweep.is_checked(): break

            # Set the frequency
            self.tab_li.number_ao_frequency.set_value(f)

            # Go for this frequency!
            self.tab_li.button_go.click()

            # Update the GUI
            self.window.process_events()

        # Uncheck it when done
        self.tab_li.button_sweep.set_checked(False)

    def _li_settings_changed(self, *a):
        """
        If someone changed a setting in the lockin tab.
        """
        f, c, N, r, n = self._li_get_frequency_cycles_samples_rate_rateindex()

        # Update the frequency
        self.tab_li.number_ao_frequency.set_value(f,block_events=True)

        # Trigger a reconfigure on the next demod
        self._li_needs_configure_ao_ai = True

    def _li_get_frequency_cycles_samples_rate_rateindex(self):
        """
        Returns the
        nearest frequency,
        number of cycles for this frequency,
        number of samples to generate it,
        the rate, and the rate's index.
        """
        s = self.tab_li.settings

        # Calculate best / lowest allowed rate
        ro, no = self._li_get_output_rate_and_index()

        # Target period
        f_target = self.tab_li.number_ao_frequency.get_value()

        # If zero, it's simple
        if not f_target: return f_target, 1, s['Output/Min_Buffer'], ro, no

        # Now, given this rate, calculate the number of points needed to make one cycle.
        N1 = ro / f_target # This is a float with a remainder

        # The goal now is to add an integer number of these cycles up to the
        # Max_Buffer and look for the one with the smallest remainder.
        max_cycles = int(        s['Output/Max_Buffer']/N1 )
        min_cycles = int(_n.ceil(s['Output/Min_Buffer']/N1))

        # List of options to search
        options   = _n.array(range(min_cycles,max_cycles+1)) * N1 # Possible floats

        # How close each option is to an integer.
        residuals = _n.minimum(abs(options-_n.ceil(options)), abs(options-_n.floor(options)))

        # Now we can get the number of cycles
        c = _n.where(residuals==min(residuals))[0][0]

        # Now we can get the number of samples
        N = int(_n.round(N1*(c+min_cycles)))

        # If this is below the minimum value, set it to the minimum
        if N < s['Output/Min_Buffer']: N = s['Output/Min_Buffer']

        # Update the GUI
        self.tab_li.label_samples.set_text('AO Buffer: '+str(N))

        # Now, given this number of points, which might include several oscillations,
        # calculate the actual closest frequency
        df = ro/N # Frequency step
        n  = int(_n.round(self.tab_li.number_ao_frequency.get_value()/df)) # Number of cycles
        f  = n*df # Actual frequency that fits.

        return f, n, N, ro, no

    def _li_configure_ao_ai(self):
        """
        Configures the output and input for lock-in.
        """
        ### Remember the settings

        self._pre_li_ao_settings = self.tab_ao.settings.send_to_databox_header()
        self._pre_li_ai_settings = self.tab_ai.settings.send_to_databox_header()

        ### Set up the AO tab.

        self.tab_ao.checkbox_auto.set_checked(False)
        so = self.tab_ao.settings
        sl = self.tab_li.settings

        # Get the frequency, number of cycles, buffer size, output rate, and
        # output rate index.
        f, c, N, ro, no = self._li_get_frequency_cycles_samples_rate_rateindex()
        so['Ch1']         = so['Ch2']         = True
        so['Ch1/Loop']    = so['Ch2/Loop']    = True
        so['Ch1/Samples'] = so['Ch2/Samples'] = N
        so.set_list_index('Ch1/Rate', no)
        so.set_list_index('Ch2/Rate', no)

        # Use one channel for triggering and one for output
        cht = sl['Output/Trigger_Out']
        if cht == 'Ch1': chs = 'Ch2'
        else:            chs = 'Ch1'

        # Signal out channel
        so[chs+'/Waveform']       = 'Sine'
        so[chs+'/Sine/Amplitude'] = sl['Output/Amplitude']
        so[chs+'/Sine/Cycles']    = c
        so[chs+'/Sine/Offset']    = 0
        so[chs+'/Sine/Phase']     = 90

        # Trigger out channel
        so[cht+'/Waveform']     = 'Square'
        so[cht+'/Square/Start'] = 0

        ### Set up the AI tab.

        si = self.tab_ai.settings

        # Just match the analog out
        si.set_list_index('Rate', no)

        # Get the input rate number
        ri = self._ai_get_rate()

        # Calcualte how many samples to record after the delay
        # If f is nonzero, we need an integer number of cycles * time per cycle * the rate
        if f: samples = _n.ceil(sl['Input/Measure']*f) / f * ri

        # Otherwise, we just use the time.
        else: samples = sl['Input/Measure'] * ri

        # Figure out the max buffer length that is an integer number of periods
        #                floor( max time * frequency ) * rate
        max_buffer = int(_n.floor(sl['Input/Max_Buffer']/ri*f)*ri/f)

        # Don't go over budget!
        si['Samples'] = min(samples, max_buffer)

        # How long to delay after the trigger
        si['Trigger/Delay'] = 0

        # Set the timeout to something reasonable
        si['Timeout'] = max(5*(si['Samples']/ri + si['Trigger/Delay']), 1)

        # Other settings
        si['Iterations'] = 1

        if sl['Input/Trigger_In'] == 'Ch1':
            si['Trigger/In']            = 'Ch1'
            si['Trigger/Ch1']           = 'Analog'
            si['Trigger/Ch1/Condition'] = 'Rising'

        elif sl['Input/Trigger_In'] == 'Ch2':
            si['Trigger/In']            = 'Ch2'
            si['Trigger/Ch2']           = 'Analog'
            si['Trigger/Ch2/Condition'] = 'Rising'

        # Otherwise it's external
        else:
            si['Trigger/In']            = 'Ch1'
            si['Trigger/Ch1']           = 'External'
            si['Trigger/Ch1/Condition'] = 'Rising'

        # Also update the demod frequency
        self.tab_li.number_demod_frequency.set_value(f)

        # Make sure everything updates!
        self.window.process_events()

    def _li_get_output_rate_and_index(self):
        """
        Returns the rate and index of said rate.
        """
        s = self.tab_li.settings
        if s['Output/Rate'] == 'Automatic':

            # Goal number of points, frequency and rate
            N = s['Output/Min_Buffer']
            F = self.tab_li.number_ao_frequency.get_value()
            R = F*N

            # Now find the first rate higher than this
            for n in range(len(self._ao_rates)):
                r = self._ao_rates[-n-1]
                if r > R: break

            # Now get the actual frequency associated with this number of steps
            return r, self._ao_rates.index(r)

        # Rate is specified by the user
        else:
            n = s.get_list_index('Output/Rate')
            return self._ao_rates[n], n

    def _li_get_output_rate(self):
        """
        Returns the "best" rate for the given settings.
        """
        return self._li_get_output_rate_and_index()[0]

    def _ao_button_stop_clicked(self, *a):
        """
        Stop the ao.
        """
        self.ao.zero()

    def _ao_button_send_clicked(self, *a):
        """
        Sends the current design waveform to
        """
        if not self.tab_ao.button_send.is_checked(): return
        self.window.process_events()

        s = self.tab_ao.settings
        p = self.tab_ao.plot_design

        # Enable / disable outputs
        self.ao.set_enabled(s['Ch1'], s['Ch2'])

        # Set the rates
        self.ao.set_sample_rates(self._ao_get_rate('Ch1'), self._ao_get_rate('Ch2'))

        # Set Loop mode (BUG: NEED TO DO THIS TWICE FOR IT TO STICK)
        self.ao.set_loop_modes(s['Ch1/Loop'], s['Ch2/Loop'])
        self.ao.set_loop_modes(s['Ch1/Loop'], s['Ch2/Loop'])

        # Dual sync'd mode
        if s['Ch1'] and s['Ch2']: self.ao.send_samples_dual(p['V1'], p['V2'])

        # Individual channel basis
        else:
            if s['Ch1']: self.ao.send_samples(1, p['V1'])
            if s['Ch2']: self.ao.send_samples(2, p['V2'])




        # Clear and replace the send plot info
        ps = self.tab_ao.plot_sent
        ps.clear()
        ps.copy_all(p)
        ps.plot(); self.window.process_events()

        self.tab_ao.button_send.set_checked(False)
        self.window.process_events()

    def _ao_after_plot_design_load(self):
        """
        Do stuff after the plot is loaded. Update sample rate, samples, switch
        to custom mode, etc.
        """
        s = self.tab_ao.settings
        p = self.tab_ao.plot_design
        s.update(p)

    def _ao_get_rate(self, c):
        """
        Returns the rate for the specified channel ('Ch1', or 'Ch2').
        """
        return self._ao_rates[self.tab_ao.settings.get_list_index(c+'/Rate')]

    def _ao_update_waveform_frequency(self, c, w):
        """
        Returns the frequency for the settings under the specified root (e.g. c='Ch1', w='Sine')
        """
        s = self.tab_ao.settings
        s.set_value(c+'/'+w, self._ao_get_rate(c)/s[c+'/Samples']*s[c+'/'+w+'/Cycles'],
            block_all_signals=True)

    def _ao_settings_add_channel(self, c):
        """
        Adds everything for the specified channel ('Ch1' or 'Ch2') to the tab_ao.settings.
        """
        s = self.tab_ao.settings

        s.add_parameter(c, True, tip='Enable analog output 1')
        s.add_parameter(c+'/Rate', ['75 MHz', '7.5 MHz', '750 kHz', '75 kHz', '7.5 kHz', '750 Hz'], tip='How fast to output voltages.')
        s.add_parameter(c+'/Samples',  8000, bounds=(1,None), dec=True, suffix='S', siPrefix=True, tip='Number of samples in the waveform. Above 8192, this number depends on USB bandwidth, I think.')
        s.add_parameter(c+'/Loop', True, tip='Whether the waveform should loop.')
        s.add_parameter(c+'/Waveform', ['Sine', 'Square', 'Pulse_Decay', 'Custom'], tip='Choose a waveform.')

        # Sine
        s.add_parameter(c+'/Sine',           0.0, suffix='Hz', siPrefix=True, tip='Frequency (from settings below).', readonly=True)
        s.add_parameter(c+'/Sine/Cycles',      1, dec=True, tip='How many times to repeat the waveform within the specified number of samples.' )
        s.add_parameter(c+'/Sine/Amplitude', 0.1, suffix='V', siPrefix=True, tip='Amplitude (not peak-to-peak).')
        s.add_parameter(c+'/Sine/Offset',    0.0, suffix='V', siPrefix=True, tip='Offset.')
        s.add_parameter(c+'/Sine/Phase',     0.0, step=5, suffix=' deg', tip='Phase of sine (90 corresponds to cosine).')

        # Square
        s.add_parameter(c+'/Square',       0.0, suffix='Hz', siPrefix=True, tip='Frequency (from settings below).', readonly=True)
        s.add_parameter(c+'/Square/Cycles',  1, dec=True, tip='How many times to repeat the waveform within the specified number of samples.' )
        s.add_parameter(c+'/Square/High',  0.1, suffix='V', siPrefix=True, tip='High value.')
        s.add_parameter(c+'/Square/Low',   0.0, suffix='V', siPrefix=True, tip='Low value.')
        s.add_parameter(c+'/Square/Start', 0.0, step=0.01, bounds=(0,1), tip='Fractional position within a cycle where the voltage goes high.')
        s.add_parameter(c+'/Square/Width', 0.5, step=0.01, bounds=(0,1), tip='Fractional width of square pulse within a cycle.')

        # Square
        s.add_parameter(c+'/Pulse_Decay/Amplitude',  0.1,   suffix='V',  siPrefix=True, tip='Pulse amplitude.')
        s.add_parameter(c+'/Pulse_Decay/Offset',     0.0,   suffix='V',  siPrefix=True, tip='Baseline offset.')
        s.add_parameter(c+'/Pulse_Decay/Tau',        10e-6, suffix='s',  siPrefix=True, dec=True, tip='Exponential decay time constant.')
        s.add_parameter(c+'/Pulse_Decay/Zero',       False, tip='Whether to zero the output voltage at the end of the pulse.')

    def _ao_settings_changed(self, *a):
        """
        When someone changes the ao settings, update the waveform.
        """
        # Select the appropriate waveform
        for c in ['Ch1', 'Ch2']: self._ao_settings_select_waveform(c)

        # Update the other parameters and generate waveforms
        self._ao_update_design()

        # If we're autosending
        if self.tab_ao.checkbox_auto.is_checked(): self.tab_ao.button_send.click()

    def _ao_settings_select_waveform(self, c):
        """
        Shows and hides the waveform menus based on the selected value.
        c = 'Ch1' or 'Ch2'.
        """
        # Show and hide waveform designers
        s = self.tab_ao.settings
        for w in ['Sine', 'Square', 'Pulse_Decay']: s.hide_parameter(c+'/'+w, w == s[c+'/Waveform'])

    def _ao_update_design(self):
        """
        Updates the design waveform based on the current settings.
        """
        s = self.tab_ao.settings

        # Calculate the frequencies from the Repetitions etc
        for w in ['Sine', 'Square']:
            self._ao_update_waveform_frequency('Ch1', w)
            self._ao_update_waveform_frequency('Ch2', w)

        # Overwrite what's in there.
        p = self.tab_ao.plot_design
        s.send_to_databox_header(p)
        self._ao_generate_waveform('Ch1')
        self._ao_generate_waveform('Ch2')

        # Plot it
        p.plot(); self.window.process_events()

    def _ao_generate_waveform(self, c):
        """
        Generates the waveform in settings channel c (can be 'Ch1' or 'Ch2'), and
        sends this to the design plotter.
        """
        s = self.tab_ao.settings    # Shortcut to settings
        p = self.tab_ao.plot_design # Shortcut to plotter
        w = s[c+'/Waveform']        # Waveform string, e.g. 'Sine'
        N = s[c+'/Samples']         # Number of samples
        R = self._ao_get_rate(c)    # Sampling rate in Hz

        # Get the time array
        t = p['t'+c[-1]] = _n.linspace(0,(N-1)/R,N)

        # Don't adjust the voltages if custom mode unless the lengths don't match
        if w == 'Custom':
            if not len(t) == len(p['V'+c[-1]]): p['V'+c[-1]] = _n.zeros(len(t))
            return

        # Get the frequency and period for the other modes
        if w in ['Sine', 'Square']:
            f = s[c+'/'+w]              # Frequency in Hz
            T = 1.0/f                   # Period (sec)

        # Get the waveform
        if   w == 'Sine': p['V'+c[-1]] = s[c+'/Sine/Offset'] + s[c+'/Sine/Amplitude']*_n.sin((2*_n.pi*f)*t + s[c+'/Sine/Phase']*_n.pi/180.0)
        elif w == 'Square':

            # Start with the "low" values
            v = _n.full(N, s[c+'/Square/Low'])

            # Get the pulse up and down times for one cycle
            t1 = T*s[c+'/Square/Start']
            t2 = T*s[c+'/Square/Width'] + t1

            # Loop over the segments adding "high" values
            for n in range(s[c+'/Square/Cycles']):

                # Start of cycle
                t0 = n*T

                # Set the high value for this cycle
                v[_n.logical_and(t>=t0+t1, t<t0+t2)] = s[c+'/Square/High']

            # Set it
            p['V'+c[-1]] = v

        elif w == 'Pulse_Decay':
            p['V'+c[-1]] = s[c+'/Pulse_Decay/Offset'] + s[c+'/Pulse_Decay/Amplitude']*_n.exp(-t/s[c+'/Pulse_Decay/Tau'])
            if s[c+'/Pulse_Decay/Zero']:
                p['V'+c[-1]][-1] = 0





    def _button_connect_clicked(self, *a):
        """
        Called when someone clicks the "connect" button.
        """
        # Get the adalm2000's URI
        uri = self.combo_contexts.get_text()

        # Connect!
        self.api = adalm2000_api(uri)

        # Easier coding
        self.ai    = self.api.ai
        self.ao    = self.api.ao
        self.power = self.api.power

        # If simulation mode, make this clear
        if self.api.simulation_mode:
            self.label_status.set_text('*** SIMULATION MODE ***')
            self.label_status.set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
            self.button_connect.set_colors('black', 'pink')

        # Otherwise, give some information
        else:
            self.label_status.set_text(self.api.get_infostring())
            self.label_status.set_colors('cyan')

        # For now, just disable these
        self.button_connect.disable()
        self.combo_contexts.disable()
        self.tabs.enable()

        # Reset the power supply
        self._power_settings_changed()

        # Start the timer
        self.tab_power.timer.start()
        self.t0 = _t.time()

    def _power_timer_tick(self, *a):
        """
        Called whenever the power timer ticks (for updating readings).
        """
        Vp = Vm = None

        # Read if we're supposed to
        if self.tab_power.button_monitor_Vp.is_checked(): Vp = self.api.power.get_Vp()
        if self.tab_power.button_monitor_Vm.is_checked(): Vm = self.api.power.get_Vm()

        data_point = [_t.time()-self.t0]

        # Update the labels and plot
        if Vp == None:
            self.tab_power.label_Vp.set_text('(not measured)').set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
        else:
            self.tab_power.label_Vp.set_text('%.3f V' % Vp).set_colors(None)
            data_point.append(Vp)

        if Vm == None:
            self.tab_power.label_Vm.set_text('(not measured)').set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
        else:
            self.tab_power.label_Vm.set_text('%.3f V' % Vm).set_colors(None)
            data_point.append(Vm)

        # Add it to the history
        self.tab_power.plot.append_row(data_point, ['t-t0', 'V+', 'V-'])
        self.tab_power.plot.plot()


    def _power_settings_changed(self, *a):
        """
        Called whenever someone changes a setting in the power tab.
        """
        if self.tab_power.button_enable_Vp.is_checked(): Vp = self.tab_power.number_set_Vp.get_value()
        else: Vp = 0

        if self.tab_power.button_enable_Vm.is_checked(): Vm = self.tab_power.number_set_Vm.get_value()
        else: Vm = 0

        self.api.power.set_Vp(Vp)
        self.api.power.set_Vm(Vm)

        return

    def _libregexdisp_ctl(self, opposite=False):
        # Yeah, so it's not actualy that well hidden. Congrats. If you
        # decide to use this feature you had better know *exactly* what
        # it's doing! ;) Love, Jack
        self.tab_ai.A1.settings.hide_parameter('Average/Error', opposite)
        self.tab_ai.A2.settings.hide_parameter('Average/Error', opposite)
        self.tab_ai.A3.settings.hide_parameter('Average/Error', opposite)
        self.tab_ai.B1.settings.hide_parameter('Average/Error', opposite)
        self.tab_ai.B2.settings.hide_parameter('Average/Error', opposite)
        self.tab_ai.B3.settings.hide_parameter('Average/Error', opposite)

    def _ai_get_rate(self):
        """
        Returns the rate.
        """
        return self._ai_rates[self.tab_ai.settings.get_list_index('Rate')]

    def _ai_settings_changed(self, *a):
        """
        Called when specific settings change.
        """
        self.tab_ai.plot_raw.ROIs[0][0].setPos((self.tab_ai.settings['Trigger/Delay'], 0))
        self.tab_ai.plot_raw.ROIs[1][0].setPos((self.tab_ai.settings['Trigger/Delay'], 0))
        self.tab_ai.plot_raw.ROIs[0][1].setPos((0, self.tab_ai.settings['Trigger/Ch1/Level']))
        self.tab_ai.plot_raw.ROIs[1][1].setPos((0, self.tab_ai.settings['Trigger/Ch2/Level']))

        if(self.button_connect.is_checked()): self._ai_cursor_drag()

    def _ai_cursor_drag(self, *a):
        """
        Called whenever someone moves a cursor in the analog in tab.
        """
        # Time cursors should set each other.
        if len(a) and a[0] == self.tab_ai.plot_raw.ROIs[0][0]:

            # Get the x-position and update the other stuff
            x = a[0].getPos()[0]
            self.tab_ai.plot_raw.ROIs[1][0].setPos((x,0))
            self.tab_ai.settings['Trigger/Delay'] = x

        elif len(a) and a[0] == self.tab_ai.plot_raw.ROIs[1][0]:

            # Get the x-position and update the other stuff
            x = a[0].getPos()[0]
            self.tab_ai.plot_raw.ROIs[0][0].setPos((x,0))
            self.tab_ai.settings['Trigger/Delay'] = x

        # Other cursors are simpler.
        else:

            # Trigger level cursors
            V1 = self.tab_ai.plot_raw.ROIs[0][1].getPos()[1]
            V2 = self.tab_ai.plot_raw.ROIs[1][1].getPos()[1]

            # Set them on the hardware if we are not in simulation mode
            if not self.api.simulation_mode:
                self.ai.set_trigger_levels(V1, V2)
                V1, V2 = self.ai.get_trigger_levels()

            # Update the cursor to the actual value
            self.tab_ai.plot_raw.ROIs[0][1].setPos((0,V1))
            self.tab_ai.plot_raw.ROIs[1][1].setPos((0,V2))

            # Trigger levels
            self.tab_ai.settings.set_value('Trigger/Ch1/Level', V1, block_all_signals=True)
            self.tab_ai.settings.set_value('Trigger/Ch2/Level', V2, block_all_signals=True)

    def _ai_button_auto_clicked(self, *a):
        """
        Homes the trigger.
        """
        p = self.tab_ai.plot_raw
        s = self.tab_ai.settings

        # If there is data, use the midpoints for the level
        if len(p.ckeys) > 1: s['Trigger/Ch1/Level'] = 0.5*(max(p[1])+min(p[1]))
        else:                s['Trigger/Ch1/Level'] = 0.0;
        if len(p.ckeys) > 2: s['Trigger/Ch2/Level'] = 0.5*(max(p[2])+min(p[2]))
        else:                s['Trigger/Ch2/Level'] = 0.0;

        # Set the delay to zero
        s['Trigger/Delay'] = 0

    def _ai_button_acquire_clicked(self, *a):
        """
        Called when someone clicks the "acquire" button on the ADC tab.
        """
        # If we just turned it off, poop out instead of starting another loop.
        if not self.tab_ai.button_acquire.is_checked(): return

        # Easy coding
        s  = self.tab_ai.settings
        p  = self.tab_ai.plot_raw

        # Iteration number
        n = 0; self.tab_ai.label_info.set_text('Iteration: '+str(n))

        # Loop until we've finishe our iterations, someone pushed the button, or forever (iterations=0)
        while self.tab_ai.button_acquire.is_checked() and \
            (n < s['Iterations'] or s['Iterations'] < 1):

            # Enable channels (THIS DOESN'T HAVE AN EFFECT!)
            # self.api.ai.enableChannel(0, s['Ch1'])
            # self.api.ai.enableChannel(1, s['Ch2'])

            # Set the timeout
            self.api.set_timeout(int(s['Timeout']*1000));

            # Set the sampling rate (variable 'rate' used below)
            rate = self._ai_rates[s.get_list_index('Rate')]
            self.ai.set_sample_rate(rate)

            # Set the ranges
            self.ai.set_range_big(s['Ch1_Range']=='25V', s['Ch2_Range']=='25V')

            # Set the trigger source, out, conditions, and levels

            self.ai.set_trigger_in  (s.get_list_index('Trigger/In'))
            self.ai.set_trigger_out (s.get_list_index('Trigger/Out'))
            t_delay = self.ai.set_trigger_delay(s['Trigger/Delay'])

            self.ai.set_trigger_modes(s.get_list_index('Trigger/Ch1'),
                                      s.get_list_index('Trigger/Ch2'))
            self.ai.set_trigger_conditions(s.get_list_index('Trigger/Ch1/Condition'),
                                           s.get_list_index('Trigger/Ch2/Condition'))
            self.ai.set_trigger_levels(s['Trigger/Ch1/Level'],
                                       s['Trigger/Ch2/Level'])
            self.ai.set_trigger_hystereses(s['Trigger/Ch1/Hysteresis'],
                                           s['Trigger/Ch2/Hysteresis'])

            # Get the time array
            ts = _n.linspace(t_delay, t_delay + (s['Samples']-1)/rate, s['Samples'])

            # Get the data
            self.tab_ai.button_onair.set_checked(True).set_colors('red', 'pink'); self.window.process_events();
            vs = self.ai.get_samples(s['Samples'])
            self.tab_ai.button_onair.set_checked(False).set_colors(None, None); self.window.process_events();

            # If vs==None it's a timeout
            if vs:
                # Clear and send the current settings to plotter
                p.clear()
                s.send_to_databox_header(p)
                self.tab_ao.settings.send_to_databox_header(p)
                self.tab_li.settings.send_to_databox_header(p)
                p.h(t=_t.time()-self.t0, t0=self.t0)

                # Add columns
                p['Time(s)'] = ts
                for i in range(len(vs)): p['V'+str(i+1)] = vs[i]

                # Update the plot and autosave if that's enabled
                p.plot()
                p.autosave()

                # External analysis
                self.process_data()

                # Send it to the demodulator
                if self.tab_li.checkbox_enable.is_checked(): self.demodulate()

                # Increment, update move on.
                n += 1
                self.tab_ai.label_info.set_text('Iteration: '+str(n))

            # Timeout
            elif self.tab_ai.settings['Timeout/Then_What'] == 'Quit': break
            elif self.tab_ai.settings['Timeout/Then_What'] == 'Immediate':

                # If we're already in immediate mode, something more serious is at play.
                if  self.tab_ai.settings['Trigger/Ch1'] == 'Immediate' \
                and self.tab_ai.settings['Trigger/Ch2'] == 'Immediate': break

                # Set to immediate mode to get *some* data
                self.tab_ai.settings['Trigger/Ch1'] = 'Immediate'
                self.tab_ai.settings['Trigger/Ch2'] = 'Immediate'

                # Warn the demodders know it's not triggered.
                if self.tab_li.button_go.is_checked():
                    self.tab_li.button_go.set_colors('white', 'red')

            # Let the user interact
            self.window.process_events()

        # Pop the button when we're done.
        self.tab_ai.button_acquire.set_checked(False)

    def after_load_ai_plot_raw(self):
        """
        What to do after loading a file.
        """
        # update the settings with the file's header info
        self.settings.update(self.plot_raw)

        # Run the analysis
        self.process_data()

    def process_data(self):
        """
        Do the analysis after each acquisition.
        """
        # Massage the data
        self.tab_ai.A1.run().plot.autosave()
        self.tab_ai.A2.run().plot.autosave()
        self.tab_ai.A3.run().plot.autosave()
        self.tab_ai.B1.run().plot.autosave()
        self.tab_ai.B2.run().plot.autosave()
        self.tab_ai.B3.run().plot.autosave()

        # Additional analysis that is not of general use.
        self.process_data2()

    def process_data2(self):
        """
        Overwrite this function to add your own crazy analysis after all the
        "Standard" analyzers are complete.
        """
        return

class sillyscope_api(_mp.visa_tools.visa_api_base):
    """
    Class for talking to a Tektronix TDS/TBS 1000 series and Rigol 1000 B/D/E/Z
    sillyscopes.

    Parameters
    ----------
    name='TDS1012B'
        Name of the scope, as it appears in the VISA resource manager.

    pyvisa_py=False
        Set to True if using pyvisa-py instead of, e.g., R&S VISA or NI-VISA.

    simulation=False
        Set to True to enable simulation mode.

    timeout=3e3
        Command timeout (ms)

    write_sleep=0.01
        How long to sleep after a write operation (sec)

    """


    def __init__(self, name='TDS1012B', pyvisa_py=False, simulation=False, timeout=3e3, write_sleep=0.0):
        if not _mp._visa: _s._warn('You need to install pyvisa to use the sillyscopes.')

        # Run the basic stuff
        _mp.visa_tools.visa_api_base.__init__(self, name=name, pyvisa_py=pyvisa_py, simulation=simulation, timeout=timeout, write_sleep=write_sleep)

        # Simulation settings
        self._simulation_sleep  = 0.01
        self._simulation_points = 1200

        # Set up the info
        self.t_duty_cycle = 0
        self.t_get_waveform  = 0
        self.previous_header = dict()
        self.previous_header[1] = dict(xzero1=0, xmultiplier1=1, yzero1=0, ymultiplier1=1)
        self.previous_header[2] = dict(xzero2=0, xmultiplier2=1, yzero2=0, ymultiplier2=1)
        self.previous_header[3] = dict(xzero3=0, xmultiplier3=1, yzero3=0, ymultiplier3=1)
        self.previous_header[4] = dict(xzero4=0, xmultiplier4=1, yzero4=0, ymultiplier4=1)
        self.model = None
        self._channel = 1


        # Remember if it's a Tektronix scope
        if self.idn[0:9] == 'TEKTRONIX': self.model='TEKTRONIX'

        # Need to distinguish 'Rigol Technologies,DS1052E,DS1ET161453620,00.04.01.00.02'
        # Which is janky and not working. (What is the GD data format??)
        elif self.idn[0:5].upper() == 'RIGOL':

            # Get the model string
            m = self.idn.split(',')[1]

            # Find out if it's a d/e or a z:
            if   m[-1] in ['Z']: self.model='RIGOLZ'
            elif m[-1] in ['B']: self.model='RIGOLB'
            else:                self.model='RIGOLDE'

        # Poop out.
        else: self.model=None

        # Set the type of encoding for the binary data returned
        self.set_binary_encoding()



    # These can be modified later to make them safe, add delays, etc.
    def command(self, message='*IDN?'):
        """
        Runs a query() if there is a question mark, and a write() if there is not.
        """
        if message.find('?') >= 0: return self.query(message)
        else:                      return self.write(message)

    def query(self, message='*IDN?'):
        """
        Sends the supplied message and returns the response.
        """
        _debug('query('+"'"+message+"'"+')')

        if self.instrument == None: return
        else:                       return self.instrument.query(message)

    def write(self, message):
        """
        Writes the supplied message.
        """
        _debug('write('+"'"+message+"'"+')')

        if self.instrument == None: return
        else:                       return self.instrument.write(message)

    def read (self):
        """
        Reads a message and returns it.
        """
        _debug('read()')

        if self.instrument == None: return
        else:                       return self.instrument.read()

    def read_raw(self):
        """
        Reads a raw message (e.g. a binary stream) and returns it.
        """
        _debug('read_raw()')

        if self.instrument == None: return
        else:                       return self.instrument.read_raw()

    def clear(self):
        """
        Clears the display if possible.
        """
        if   self.model in ['RIGOLZ']:           self.write(':CLE')
        elif self.model in ['RIGOLB','RIGOLDE']: self.write(':DISP:CLE')

    def get_waveform(self, channel=1, convert_to_float=True, include_x=True, use_previous_header=False, binary=None):
        """
        Queries the device for the currently shown data from the specified channel,
        returning a databox with all the information.

        The databox header contains all the information required to convert
        from integer steps in x and y to time (or frequency) and voltage. If the
        databox is 'd', then the x-values are generated as

             d['x'] = d.h('xmultiplierN')*(n)

        where 'n' is the step number and N is the channel number, while
        the y-values are generated as

             d['yN'] = d.h('yzeroN') + d.h('ymultiplierN')*(v)

        where 'v' is the 'voltage' in 8-bit integer units (spanning -127 to 128
        over the full range).

        This function also times these calls and sets self.t_get_waveform to the
        total time of the function call in seconds, and self.t_duty_cycle to the
        ratio of time spent on the CURV query vs the total time.

        Parameters
        ----------
        channel=1
            Which channel to query. Must be an integer and channel 1 corresponds
            to the first channel.

        convert_to_float=True
            If True, convert the returned integers to floating point based on the
            scope range. If False, just return the integers. Note the conversion
            factors will be in the returned databox header either way.

        include_x=True
            Whether to also generate a column of data for the x-values.

        use_previous_header=False
            If True, this will not query the waveform preamble / header information,
            which is actually several times longer than the data query. The
            header information from the previous query is stored in the
            dictionary self.previous_header[channel].

        binary=None
            Can be set to any of the allowed databox (numpy), e.g. binary='float32',
            which will set the databox to this binary mode.
        """
        _debug('get_waveform()')

        # For duty cycle calculation
        t0 = _t.time()

        # For easy coding
        c = str(channel)

        # Simulation mode
        if self.instrument == None:

            # For duty cycle calculation
            t1 = _t.time()

            # Create the fake data
            d = _s.fun.generate_fake_data('5*sin(20*(1+random.normal(0,0.04,len(x)))*x + random.normal(0,4))', _n.linspace(-5,5,self._simulation_points),
                                          ey=20, include_errors=False)

            # Fake the acquisition time
            _t.sleep(self._simulation_sleep)

            # For duty cycle calculation
            t2 = _t.time()

            # Rename the columns to simulate the scope output
            d.rename_column(0, 'x')
            d.rename_column(1, 'y'+c)

            # Shorten the bitdepth
            d[1] = _n.float16(_n.int8(d[1]))

            # Get the fake header info.
            d.insert_header('xzero'+c, 1)
            d.insert_header('xoffset'+c, 0)
            d.insert_header('xmultiplier'+c, 0.1)
            d.insert_header('yzero'+c, 1)
            d.insert_header('yoffset'+c, 0)
            d.insert_header('ymultiplier'+c, 0.1)

            # Remember this for next time.
            self.previous_header[channel].update(d.headers)

            # If we're converting to float voltages
            if convert_to_float:
                d['y'+c] = d.h('yzero'+c) + d.h('ymultiplier'+c)*(d['y'+c])

            # Pop the time column if necessary
            if not include_x: d.pop(0)



        # Real deal
        else:

            # Databox to fill
            d = _s.data.databox()

            # Set the source channel
            self.set_channel(channel)

            # For duty cycle calculation
            t1 = _t.time()
            d.h(seconds_pre_waveform_query=t1)

            # Transfer the waveform information
            v = self._query_and_decode_waveform()

            _debug('_query_and_decode_waveform() done', len(v))

            # For duty cycle calculation
            t2 = _t.time()
            d.h(seconds_post_waveform_query=t2)

            # Get the waveform header

            # If we're using the previous header, just load in the values
            if use_previous_header:
                d.update_headers(self.previous_header[channel])

            # Otherwise, get a new header from the instrument.
            else: self.get_header(d)

            # If we're supposed to include time, add the time column
            if include_x:
                d['x'] = _n.arange(0, len(v), 1)
                d['x'] = d.h('xmultiplier'+c)*(d['x'])

            # If we're converting to float voltages
            if convert_to_float:
                d['y'+c] = d.h('yzero'+c) + d.h('ymultiplier'+c)*(v)
            else:
                d['y'+c] = v

        # Set the binary mode
        if not binary == None: d.h(SPINMOB_BINARY=binary)

        # For duty cycle calculation
        t3 = _t.time()
        self.t_get_waveform  = t3-t0
        if t3-t0>0: self.transfer_duty_cycle = (t2-t1)/self.t_get_waveform
        else:       print("WARNING: get_waveform() total time == 0")

        # Note the duty cycle.
        d.h(transfer_duty_cycle=self.transfer_duty_cycle)

        _debug('get_waveform() complete')
        # End of getting arrays and header information
        return d

    def trigger_single(self):
        """
        After calling self.set_mode_single_trigger(), you can call this to
        tell it to wait for the next trigger. It's up to you to check if
        the trigger is complete.
        """
        _debug('trigger_single()')

        if   self.model=='TEKTRONIX': self.write('ACQ:STATE 1')
        elif self.model=='RIGOLDE':   self.write(':RUN')
        elif self.model=='RIGOLZ':    self.write(':SING')
        elif self.model=='RIGOLB':    self.write(':KEY:SING')

        _debug('trigger_single() complete')


    def get_header(self, d=None):
        """
        Updates the header of databox d to include xoffset, xmultiplier, xzero, yoffset,
        ymultiplier, yzero. If d=None, creates a databox.
        """
        _debug('get_header()', str(d))

        if d==None: d = _s.data.databox()

        # For easier coding later
        c = str(self._channel)

        _debug('  Checking model...',
              self.model,
              self.model in ['TEKTRONIX'],
              self.model in ['RIGOLDE'],
              self.model in ['RIGOLZ','RIGOLB'])

        if self.model in ['TEKTRONIX']:
            _debug('  TEKTRONIX')

            yinc = float(self.query('WFMP:YMUL?'))

            d.insert_header('xzero'+c,       0)#float(self.query('WFMP:XZE?')))
            d.insert_header('xmultiplier'+c, float(self.query('WFMP:XIN?')))
            d.insert_header('yzero'+c,       -float(self.query('WFMP:YOF?'))*yinc)
            d.insert_header('ymultiplier'+c, yinc)


        elif self.model in ['RIGOLDE']:
            _debug('  RIGOLDE')

            # Get the increments (empirically determined f***ing manual)
            xinc = float(self.query(':TIM:SCAL?'))       * 0.02
            yinc = float(self.query(':CHAN'+c+':SCAL?')) * 0.04

            d.insert_header('xzero'+c,       0)#float(self.query(':TIM:OFFS?')))
            d.insert_header('xmultiplier'+c, xinc)
            d.insert_header('yzero'+c,       -float(self.query(':CHAN'+c+':OFFS?')))
            d.insert_header('ymultiplier'+c, yinc)



        elif self.model in ['RIGOLB']:
            _debug('  RIGOLB')

            # Convert the yoffset to the Tek format
            xinc = float(self.query(':WAV:XINC? CHAN'+c))
            yinc = float(self.query(':WAV:YINC? CHAN'+c))

            # Also get whether we're in peak detect mode, since this messes up the x-scale!
            d.insert_header('peak_detect', self.query(':ACQ:TYPE?').strip() == 'PEAK')
            if d.h('peak_detect'): xrescale=0.5
            else:                  xrescale=1.0

            d.insert_header('xzero'+c,       0)#-float(self.query(':WAV:XOR? CHAN'+c)))
            d.insert_header('xmultiplier'+c, xinc*xrescale)
            d.insert_header('yzero'+c,       -float(self.query(':WAV:YOR? CHAN'+c)))
            d.insert_header('ymultiplier'+c, yinc)



        elif self.model in ['RIGOLZ']:
            _debug('  RIGOLZ')

            # Convert the yoffset to the Tek format
            xinc = float(self.query(':WAV:XINC?'))
            yinc = float(self.query(':WAV:YINC?'))

            d.insert_header('xzero'+c,       0)#-float(self.query(':WAV:XOR?')))
            d.insert_header('xmultiplier'+c, xinc)
            d.insert_header('yzero'+c,       -float(self.query(':WAV:YOR?'))*yinc)
            d.insert_header('ymultiplier'+c, yinc)

        else:
            print('ERROR: get_header() unhandled model '+str(self.model))

        _debug('  Done with model-specifics.')

        # Remember these settings for later.
        self.previous_header[self._channel].update(d.headers)

        return d


    def _query_and_decode_waveform(self):
        """
        Queries and then parses the waveform, returning the array of (int8)
        voltages. Prior to calling this, make sure the scope is ready to
        transfer and you've run self.set_channel().
        """
        _debug('_query_and_decode_waveform()')

        empty = _n.array([], dtype=_n.float16)

        if self.model in ['TEKTRONIX']:

            # May be an option to change later
            width = 1

            if "MDO" in self.idn:
                # Get current settings for verbose/head
                head = self.query(":HEADer?")[-2]
                verb = self.query(":VERBose?")[-2]
                # Turn on verbose header for consistency in returned data.
                self.write(':HEADer 1')
                self.write(':VERBose 1')
                # Get number of points in waveform data
                n_pts = int(self.query("WFMOutpre:WFID?").split(' ')[6])
                # Set verbose/header settings to what they were previously.
                self.write(':HEADer ' + head)
                self.write(':VERBose ' + verb)
                # Set number of points to acquire to be the full waveform
                self.write('DATA:STAR 1')
                self.write('DATA:STOP %d' % n_pts)

            # Ask for the waveform and read the response
            try:
                # Get the curve raw data
                self.write('CURV?')
                s = self.read_raw()

            except:
                print('ERROR: Timeout getting curve.')
                return empty

            # Get the length of the thing specifying the data length :)
            n = int(s[1:3].decode()[0])

            # Get the length of the data set
            N = int(int(s[2:2+n].decode())/width)

            # Convert to an array of integers
            return _n.float16(_n.frombuffer(s[2+n:2+n+N*width],_n.int8))


        elif self.model in ['RIGOLDE']:
            # Ask for the data
            try:
                self.write(':WAV:DATA? CHAN%d' % self._channel)
                s = self.read_raw()

            except:
                print('ERROR: Timeout getting curve.')
                return empty

            # Get the number of characters describing the number of points
            n = int(s[1:2].decode())

            # Get the number of points
            N = int(s[2:2+n].decode())
            _debug(N)

            # Determined from measured results
            return 125 - _n.float16(_n.frombuffer(s[2+n:2+n+N], _n.uint8))


        elif self.model in ['RIGOLB']:

            # Ask for the data
            try:
                self.write(':WAV:DATA?')
                s = self.read_raw()

            except:
                print('ERROR: Timeout getting curve.')
                return empty

            # Get the number of characters describing the number of points
            n = int(s[1:2].decode())

            # Get the number of points
            N = int(s[2:2+n].decode())
            _debug(N)

            # Convert it to integers, this code is based on empirically measuring.
            return 99 - _n.float16(_n.frombuffer(s[2+n:2+n+N], _n.uint8))


        elif self.model in ['RIGOLZ']:

            # Ask for the data
            try:
                self.write(':WAV:DATA?')
                s = self.read_raw()

            except:
                print('ERROR: Timeout getting curve.')
                return empty

            # Get the number of characters describing the number of points
            n = int(s[1:2].decode())

            # Get the number of points
            N = int(s[2:2+n].decode())
            _debug(N)

            # Convert it to an array of integers.
            # This hits the rails properly on the DS1074Z, but is one step off from
            # The values reported on the main screen.
            return _n.float16(_n.frombuffer(s[2+n:2+n+N], _n.uint8)) - 127


    def set_binary_encoding(self):
        """
        Sets up the binary encoding mode for curve transfer.
        """
        _debug('set_binary_encoding()')

        if self.model in ['TEKTRONIX']:
            self.write('DATA:ENC SRI')
            self.write('DATA:WIDTH 1') # Use 2 for two bytes per point.

        elif self.model in ['RIGOLDE']:
            self.write(':WAV:POIN:MODE NORM')

        elif self.model in ['RIGOLZ', 'RIGOLB']:
            self.write(':WAV:MODE NORM') # Just get the screen. Use RAW to access the full memory.
            self.write(':WAV:FORM BYTE') # Use WORD to have two bytes per point.

        else:
            _debug('  ERROR: unhandled model '+str(self.model))

    def set_channel(self, channel=1):
        """
        Select the channel to get the waveform data.
        """
        _debug('set_channel()')

        if self.model == 'TEKTRONIX':
            self.write('DATA:SOURCE CH%d' % channel)

        elif self.model in ['RIGOLDE']:
            # DE Relies on a channel specified with the data query
            pass

        elif self.model in ['RIGOLB', 'RIGOLZ']:
            self.write(':WAV:SOUR CHAN%d' % channel)

        else:
            _debug('  ERROR: unhandled model '+str(self.model))

        # Keep this for future use.
        self._channel = channel

    def set_mode_single_trigger(self):
        """
        Stops acquisition and sets it up to take a single trace upon the
        next self.acquire() command.
        """
        _debug('set_mode_single_trigger()', self.model)

        if self.model == 'TEKTRONIX':
            self.write('ACQ:STATE STOP')
            self.write('ACQ:STOPA SEQ')

        elif self.model in ['RIGOLZ', 'RIGOLDE', 'RIGOLB']:
            self.write(':STOP')
            self.write(':TRIG:EDGE:SWE SINGLE')





class sillyscope(_mp.visa_tools.visa_gui_base):
    """
    Graphical front-end for RIGOL 1000 B/D/E/Z and Tektronix TBS/TDS 1000.

    Parameters
    ----------
    name='sillyscope'
        Which file to use for saving the gui stuff. This will also be the first
        part of the filename for the other settings files.

    show=True
        Whether to show the window immediately.

    block=False
        Whether to block the command line while showing the window.

    pyvisa_py=False
        Whether to use pyvisa_py or not.

    """
    def __init__(self, name='sillyscope', show=True, block=False, pyvisa_py=False):
        if not _mp._visa: _s._warn('You need to install pyvisa to use the sillyscopes.')

        # Run the baseline stuff
        _mp.visa_tools.visa_gui_base.__init__(self, name=name, show=False, block=False, api=sillyscope_api, pyvisa_py=pyvisa_py, window_size=[1000,500])

        # Build the GUI
        self.window.event_close = self._event_close

        self.button_1         = self.grid_top.place_object(_g.Button('1',True).set_width(25).set_checked(True))
        self.button_2         = self.grid_top.place_object(_g.Button('2',True).set_width(25))
        self.button_3         = self.grid_top.place_object(_g.Button('3',True).set_width(25))
        self.button_4         = self.grid_top.place_object(_g.Button('4',True).set_width(25))
        self.button_acquire   = self.grid_top.place_object(_g.Button('Acquire',True).disable())
        self.number_count     = self.grid_top.place_object(_g.NumberBox(0).disable())
        self.button_onair   = self.grid_top.place_object(_g.Button('Waiting', True).set_width(70))
        self.button_transfer  = self.grid_top.place_object(_g.Button('Transfer',True).set_width(70))

        self.tabs_data = self.grid_bot.place_object(_g.TabArea(name+'_tabs_data.txt'), alignment=0)
        self.tab_raw   = self.tabs_data.add_tab('Raw')
        self.plot_raw  = self.tab_raw.place_object(_g.DataboxPlot('*.txt', name+'_plot_raw.txt'), alignment=0)

        # Keep track of previous plot
        self._previous_data = _s.data.databox()

        # Settings format
        self.settings.set_width(240)

        # Acquisition settings
        self.settings.add_parameter('Acquire/Iterations',       1,     tip='How many iterations to perform. Set to 0 to keep looping.')
        self.settings.add_parameter('Acquire/Trigger',          False, tip='Halt acquisition and arm / wait for a single trigger.')
        self.settings.add_parameter('Acquire/Get_First_Header', True,  tip='Get the header (calibration) information the first time. Disabling this will return uncalibrated data.')
        self.settings.add_parameter('Acquire/Get_All_Headers',  True,  tip='Get the header (calibration) information EVERY time. Disabling this will use the first header repeatedly.')
        self.settings.add_parameter('Acquire/Discard_Identical',False, tip='Do not continue until the data is different.')

        # Device-specific settings
        self.settings.add_parameter('Acquire/RIGOL1000BDE/Trigger_Delay', 0.05, bounds=(1e-3,10), siPrefix=True, suffix='s', dec=True, tip='How long after "trigger" command to wait before checking status. Some scopes appear to be done for a moment between the trigger command and arming.')
        self.settings.add_parameter('Acquire/RIGOL1000BDE/Unlock',        True, tip='Unlock the device\'s frong panel after acquisition.')
        self.settings.add_parameter('Acquire/RIGOL1000Z/Always_Clear',    True, tip='Clear the scope prior to acquisition even in untriggered mode (prevents duplicates but may slow acquisition).')

        # Connect all the signals
        self.settings.connect_signal_changed('Acquire/Trigger', self._settings_trigger_changed)
        self.button_acquire.signal_toggled.connect(self._button_acquire_clicked)
        self.button_1.signal_toggled.connect(self.save_gui_settings)
        self.button_2.signal_toggled.connect(self.save_gui_settings)
        self.button_3.signal_toggled.connect(self.save_gui_settings)
        self.button_4.signal_toggled.connect(self.save_gui_settings)

        # Run the base object stuff and autoload settings
        self._autosettings_controls = ['self.button_1', 'self.button_2', 'self.button_3', 'self.button_4']
        self.load_gui_settings()

        # Add additional analysis tabs
        self.tab_A1 = self.tabs_data.add_tab('A1')
        self.A1 = self.tab_A1.add(_g.DataboxProcessor('A1', self.plot_raw, '*.A1'), alignment=0)
        self.tab_A2 = self.tabs_data.add_tab('A2')
        self.A2 = self.tab_A2.add(_g.DataboxProcessor('A2', self.A1.plot,  '*.A2'), alignment=0)
        self.tab_A3 = self.tabs_data.add_tab('A3')
        self.A3 = self.tab_A3.add(_g.DataboxProcessor('A3', self.A2.plot,  '*.A3'), alignment=0)

        self.tab_B1 = self.tabs_data.add_tab('B1')
        self.B1 = self.tab_B1.add(_g.DataboxProcessor('B1', self.plot_raw, '*.B1'), alignment=0)
        self.tab_B2 = self.tabs_data.add_tab('B2')
        self.B2 = self.tab_B2.add(_g.DataboxProcessor('B2', self.B1.plot,  '*.B2'), alignment=0)
        self.tab_B3 = self.tabs_data.add_tab('B3')
        self.B3 = self.tab_B3.add(_g.DataboxProcessor('B3', self.B2.plot,  '*.B3'), alignment=0); self._libregexdisp_ctl()

        # After loading a raw file, run the processors
        self.plot_raw.after_load_file = self.after_load_file

        # Show it
        if show: self.window.show(block_command_line=block)

    def after_load_file(self):
        """
        What to do after loading a file.
        """
        # update the settings with the file's header info
        self.settings.update(self.plot_raw)

        # Run the analysis
        self.process_data()

    def process_data(self):
        """
        Do the analysis after each acquisition.
        """
        # Massage the data
        self.A1.run().plot.autosave()
        self.A2.run().plot.autosave()
        self.A3.run().plot.autosave()
        self.B1.run().plot.autosave()
        self.B2.run().plot.autosave()
        self.B3.run().plot.autosave()

        # Additional analysis that is not of general use.
        self.process_data2()

    def process_data2(self):
        """
        Overwrite this function to add your own crazy analysis after all the
        "Standard" analyzers are complete.
        """
        return

    def _after_connect(self):
        """
        Called after a successful connection.
        """
        self.button_acquire.enable()

    def _after_disconnect(self):
        """
        Called after a successful disconnect.
        """
        self.button_acquire.disable()

    def _settings_trigger_changed(self, *a):
        """
        Called when someone clicks the Trigger checkbox.
        """
        if self.settings['Acquire/Trigger']:
            self.api.set_mode_single_trigger()
            self.unlock()

    def _libregexdisp_ctl(self, opposite=False):
        # Yeah, so it's not actualy that well hidden. Congrats. If you
        # decide to use this feature you had better know *exactly* what
        # it's doing! ;) Love, Jack
        self.A1.settings.hide_parameter('Average/Error', opposite)
        self.A2.settings.hide_parameter('Average/Error', opposite)
        self.A3.settings.hide_parameter('Average/Error', opposite)
        self.B1.settings.hide_parameter('Average/Error', opposite)
        self.B2.settings.hide_parameter('Average/Error', opposite)
        self.B3.settings.hide_parameter('Average/Error', opposite)

    def acquisition_is_finished(self):
        """
        Returns True if the acquisition is complete.

        For RIGOL scopes, this uses get_waveforms(), which also updates
        self.plot_raw(), which is the best way to get the status. This avoids
        the issue of the single trigger taking time to get moving.
        """
        _debug('acquisition_is_finished()')

        if self.api.model == 'TEKTRONIX':
            _debug('  TEK')
            return not bool(int(self.api.query('ACQ:STATE?')))

        elif self.api.model == 'RIGOLZ':
            _debug('  RIGOLZ')

            # If the waveforms are empty (we cleared it!)
            self.get_waveforms(plot=False)
            if len(self.plot_raw[0]) > 0: return True
            else:                         return False

        elif self.api.model in ['RIGOLDE', 'RIGOLB']:
            _debug('  RIGOLDE/B')

            self.window.sleep(self.settings['Acquire/RIGOL1000BDE/Trigger_Delay'])
            s = self.api.query(':TRIG:STAT?').strip()
            return s == 'STOP'

    def get_waveforms(self, plot=True):
        """
        Queries all the waveforms that are enabled, overwriting self.plot_raw
        """
        _debug('get_waveforms()')


        # Find out if we should get the header
        get_header = self.settings['Acquire/Get_All_Headers']  \
                  or self.settings['Acquire/Get_First_Header'] \
                 and self.number_count.get_value() == 0

        # Tell the user we're getting data
        self.button_transfer.set_checked(True)
        self.window.process_events()

        # If we're not getting data.
        if not self.button_1.get_value() and \
           not self.button_2.get_value() and \
           not self.button_3.get_value() and \
           not self.button_4.get_value():
               self.button_transfer.set_checked(False)
               return


        # Clear the raw plot
        self.plot_raw.clear()

        # If we're supposed to get curve 1
        if self.button_1.get_value():

            # Actually get it.
            d = self.api.get_waveform(1, use_previous_header=not get_header)

            # Update the main plot
            self.plot_raw['x']  = d['x']
            self.plot_raw['y1'] = d['y1']
            self.plot_raw.copy_headers(d)
            self.window.process_events()

        # If we're supposed to get curve 2
        if self.button_2.get_value():

            # Actually get it
            d = self.api.get_waveform(2, use_previous_header=not get_header)

            # Update the main plot
            self.plot_raw['x']  = d['x']
            self.plot_raw['y2'] = d['y2']
            self.plot_raw.copy_headers(d)
            self.window.process_events()

        # If we're supposed to get curve 2
        if self.button_3.get_value():

            # Actually get it
            d = self.api.get_waveform(3, use_previous_header=not get_header)

            # Update the main plot
            self.plot_raw['x']  = d['x']
            self.plot_raw['y3'] = d['y3']
            self.plot_raw.copy_headers(d)
            self.window.process_events()

        # If we're supposed to get curve 2
        if self.button_4.get_value():

            # Actually get it
            d = self.api.get_waveform(4, use_previous_header=not get_header)

            # Update the main plot
            self.plot_raw['x']  = d['x']
            self.plot_raw['y4'] = d['y4']
            self.plot_raw.copy_headers(d)
            self.window.process_events()

        # Tell the user we're done transferring data
        self.button_transfer.set_checked(False)

        # Plot.
        if plot:
            self.plot_raw.plot()
            self.plot_raw.autosave()
            self.window.process_events()

        _debug('get_waveforms() complete')

    def unlock(self):
        """
        If we're using a RIGOLDE/B and wish to unlock, send the :FORC command.
        """
        if self.settings['Acquire/RIGOL1000BDE/Unlock']:
            if self.api.model in ['RIGOLDE']:
                self.api.write(':KEY:FORC')
            elif self.api.model in ['RIGOLB']:
                self.api.write(':KEY:LOCK DIS')

    def _setup_acquisition(self):
        """
        Sets up the GUI and scope for the acquisition loop.
        """

        # Disable the connection button
        self.button_connect.disable()

        # Reset the counter
        self.number_count.set_value(0)

        # If we're triggering, set to single sequence mode
        if self.settings['Acquire/Trigger']: self.api.set_mode_single_trigger()

    def _acquire_and_plot(self):
        """
        Acquires the data and plots it (one iteration of the loop).
        """
        # Update the user
        self.button_onair.set_checked(True)

        # Transfer the current data to the previous
        self._previous_data.clear()
        self._previous_data.copy_all(self.plot_raw)

        # Trigger
        if self.settings['Acquire/Trigger']:

            _debug('  TRIGGERING')

            # Set it to acquire the sequence.
            self.api.trigger_single() # For RigolZ, this clears the trace

            # Simulation mode: "wait" for it to finish
            _debug('  WAITING')
            if self.api.instrument == None: self.window.sleep(self.api._simulation_sleep)

            # Actual scope: wait for it to finish
            else:
                while not self.acquisition_is_finished() and self.button_acquire.is_checked():
                    self.window.sleep(0.02)

            # Tell the user it's done acquiring.
            _debug('  TRIGGERING DONE')

        # For RIGOL scopes, the most reliable / fast way to wait for a trace
        # is to clear it and keep asking for the waveform.

        # Not triggering but RIGOLZ mode: clear the data first and then wait for data
        elif self.api.model in ['RIGOLZ']:

            # Clear the scope if we're not in free running mode
            if self.settings['Acquire/RIGOL1000Z/Always_Clear']:
                self.api.write(':CLE')

            # Wait for it to complete
            while not self.acquisition_is_finished() and self.button_acquire.is_checked():
                self.window.sleep(0.005)

        self.button_onair.set_checked(False)

        # If the user hasn't canceled yet
        if self.button_acquire.is_checked():

            _debug('  getting data')

            # The Z RIGOL models best check the status by getting the waveforms
            # after clearing the scope and seeing if there is data returned.

            # Triggered RIGOLZ scopes already have the data
            if self.api.model in [None, 'TEKTRONIX', 'RIGOLDE', 'RIGOLB'] or \
               not self.settings['Acquire/Trigger']:

                   # Query the scope for the data and stuff it into the plotter
                   self.get_waveforms(plot=False)
                   _debug('  got '+str(self.plot_raw))

            _debug('  processing')

            # Increment the counter, but only if the data is new
            self.number_count.increment()

            # Decrement if it's identical to the previous trace
            is_identical=False
            if self.settings['Acquire/Discard_Identical']:
                is_identical = self.plot_raw.is_same_as(self._previous_data, headers=False)
                _debug('  Is identical to previous?', is_identical)
                if is_identical: self.number_count.increment(-1)

            # Transfer all the header info
            self.settings.send_to_databox_header(self.plot_raw)

            # Update the plot
            _debug('  plotting', len(self.plot_raw[0]), len(self.plot_raw[1]))
            self.plot_raw.plot()
            if not is_identical: self.plot_raw.autosave()

            _debug('  plotting done')
            self.window.process_events()

            # External analysis
            self.process_data()

            # End condition
            _debug('  checking end condition')
            N = self.settings['Acquire/Iterations']
            if self.number_count.get_value() >= N and not N <= 0:
                self.button_acquire.set_checked(False)

    def _post_acquisition(self):
        """
        Fixes up the GUI and scope after the acquisition loop.
        """
        # Enable the connect button
        self.button_connect.enable()

        # Unlock the RIGOL1000E front panel
        self.unlock()

    def _button_acquire_clicked(self, *a):
        """
        Get the enabled curves, storing them in plot_raw.
        """
        _debug('_button_acquire_clicked()')

        # Don't double-loop!
        if not self.button_acquire.is_checked(): return

        # Don't proceed if we have no connection
        if self.api == None:
            self.button_acquire.set_checked(False)
            self.button_acquire.disable()
            return

        # Set up the GUI and scope for acquisition.
        self._setup_acquisition()

        _debug('  beginning loop')

        # Continue until unchecked
        while self.button_acquire.is_checked(): self._acquire_and_plot()

        _debug('  loop done')

        # Fixes up the GUI and unlocks the scope
        self._post_acquisition()

    def _event_close(self, *a):
        """
        Quits acquisition loop when the window closes.
        """
        self.button_acquire.set_checked(False)

#     TO DO: Automate the continuous mode triggering on init.
#     TO DO: Import data file monitor.
class keithley_dmm_api():
    """
    This object lets you query the Keithley 199 or 2700 for voltages on any of its
    channels. It is based on old code from those before us.

    FAQ: Use shift + scan setup on the front panel to choose a channel, and
    shift + trig setup to set the trigger mode to "continuous". Finally,
    make sure the range is appropriate, such that the voltage does not overload.
    Basically, if you see a fluctuating number on the front panel, it's
    all set to take data via self.get_voltage() (see below).

    Parameters
    ----------
    name='ASRL3::INSTR'
        Visa resource name. Use R&S Tester 64-bit or NI-MAX to find this.

    pyvisa_py=False
        If True, use the all-python VISA implementation. On Windows, the simplest
        Visa implementation seems to be Rhode & Schwarz (streamlined) or NI-VISA (bloaty),
        with pyvisa_py=False.

    NOTE
    ----
    At some point we should inherit the common functionality of these visa
    objects with those found in visa_tools.py. All new instruments should be
    written this way, for sure! This instrument might be too low-level though...
    """



    def __init__(self, name='ASRL3::INSTR', pyvisa_py=False):
        if not _mp._visa: _s._warn('You need to install pyvisa to use the Keithley DMMs.')

        # Create a resource management object
        if _mp._visa:
            if pyvisa_py: self.resource_manager = _mp._visa.ResourceManager('@py')
            else:         self.resource_manager = _mp._visa.ResourceManager()
        else: self.resource_manager = None

        # Get time t=t0
        self._t0 = _time.time()

        # Try to open the instrument.
        try:
            self.instrument = self.resource_manager.open_resource(name)

            # Test that it's responding and figure out the type.
            try:
                # Clear out the buffer, in case the instrument was
                # Just turned on.
                self.read()

                # Ask for the model identifier
                s = self.query('U0X')

                # DMM model 199
                if s[0:3] in ['100', '199']: self.model = 'KEITHLEY199'
                else:
                    print("ERROR: Currently we only handle Keithley 199 DMMs")
                    self.instrument.close()
                    self.instrument = None

            except:
                print("ERROR: Instrument did not reply to ID query. Entering simulation mode.")
                self.instrument.close()
                self.instrument = None

        except:
            self.instrument = None
            if self.resource_manager:
                print("ERROR: Could not open instrument. Entering simulation mode.")
                print("Available Instruments:")
                for name in self.resource_manager.list_resources(): print("  "+name)

    def write(self, message, process_events=False):
        """
        Writes the supplied message.

        Parameters
        ----------
        message
            String message to send to the DMM.

        process_events=False
            Optional function to be called in between communications, e.g., to
            update a gui.
        """
        _debug('write('+"'"+message+"'"+')')

        if self.instrument == None: s = None
        else:                       s = self.instrument.write(message)

        if process_events: process_events()
        return s

    def read(self, process_events=False):
        """
        Reads a message and returns it.

        Parameters
        ----------
        process_events=False
            Optional function to be called in between communications, e.g., to
            update a gui.
        """
        _debug('read()')
        self.write('++read 10')

        if process_events: process_events()

        if self.instrument == None: response = ''
        else:                       response = self.instrument.read()

        if process_events: process_events()

        _debug('  '+repr(response))
        return response.strip()

    def query(self, message='U0X', process_events=False):
        """
        Writes the supplied message and reads the response.
        """
        _debug("query('"+message+"')")

        self.write(message, process_events)
        return self.read(process_events)

    def reset(self):
        """
        We should look up the command that is actually sent.
        """
        if self._device_name == "KEITHLEY199":
            self.write("L0XT3G5S1X")
        elif self._device_name == "KEITHLEY2700":
            self.write("INIT:CONT OFF")
            self.write("CONF:VOLT:DC")

    def unlock(self):
        """
        Tells the Keithley to listen to the front panel buttons and ignore instructions from the computer.
        """
        self.write("++loc")

    def lock(self):
        """
        Tells the Keithley to ignore the front panel buttons and listen to instructions from the computer.
        """
        self.write("++llo")

    def get_voltage(self, channel=1, process_events=False):
        """
        Returns the time just after reading the voltage and voltage value
        for the supplied channel.

        Parameters
        ----------
        channel=0:
            Channel number to read (integer).
        process_events=False:
            Optional function that will run whenever possible
            (e.g., to update a gui).
        """
        # Simulation mode
        if self.instrument == None:
            _t.sleep(0.4)
            return _time.time() - self._t0, _n.random.rand()

        # Real deal
        elif self.model == 'KEITHLEY199':

            # Select the channel
            self.write("F0R0N%dX" % channel, process_events)

            # Ask for the voltage & get rid of the garbage
            try:
                s = self.read(process_events)
            except:
                print("ERROR: Timeout on channel "+str(channel))
                return _time.time() - self._t0, _n.nan

            # Return the voltage
            try:
                return _time.time() - self._t0, float(s[4:].strip())
            except:
                print("ERROR: Bad format "+repr(s))
                return _time.time() - self._t0, _n.nan

#            # Tell it to trigger
#            self.write("++trg")
#
#            # Apparently we poll and see if it switched from 0 to 16.
#            # When it switched to 16, the measurement is done.
#            result = 0 # Indicator that measurement is done
#            n      = 0 # Timeout integer
#            while not result == 16 and n < 500:
#
#                # Don't overload the buffer.
#                _time.sleep(0.01)
#                self.write("++spoll")
#                result = int(self.read().strip())
#
#            # This waiting part made an infinite loop at 16.
#            for n in range(10):
#                self.write("++spoll")
#                if 8 & int(self.read()):
#                    break
#        # Not tested by Jack, but probably the visa approach is much better.
#        if "Keithley 2700" == self._device_name:
#            self.write("ROUT:CLOS (@10%d)"%channel)
#            self.write("READ?")
#            resp = self.read()
#            words = resp.split(",")
#            if 3 != len(words):
#                raise RuntimeError
#            if "VDC" != words[0][-3:]:
#                raise RuntimeError
#            return float(words[0][0:-3])

    def close(self):
        """
        Closes the connection to the device.
        """
        _debug("close()")
        if not self.instrument == None: self.instrument.close()


class keithley_dmm(_g.BaseObject):
    """
    Graphical front-end for the Keithley 199 DMM.

    Parameters
    ----------
    autosettings_path='keithley_dmm'
        Which file to use for saving the gui stuff. This will also be the first
        part of the filename for the other settings files.

    pyvisa_py=False
        Whether to use pyvisa_py or not.

    block=False
        Whether to block the command line while showing the window.
    """
    def __init__(self, autosettings_path='keithley_dmm', pyvisa_py=False, block=False):
        if not _mp._visa: _s._warn('You need to install pyvisa to use the Keithley DMMs.')

        # No scope selected yet
        self.api = None

        # Internal parameters
        self._pyvisa_py = pyvisa_py

        # Build the GUI
        self.window    = _g.Window('Keithley DMM', autosettings_path=autosettings_path+'_window')
        self.window.event_close = self.event_close
        self.grid_top  = self.window.place_object(_g.GridLayout(False))
        self.window.new_autorow()
        self.grid_bot  = self.window.place_object(_g.GridLayout(False), alignment=0)

        self.button_connect   = self.grid_top.place_object(_g.Button('Connect', True, False))

        # Button list for channels
        self.buttons = []
        for n in range(8):
            self.buttons.append(self.grid_top.place_object(_g.Button(str(n+1),True, True).set_width(25)))
            self.buttons[n].signal_toggled.connect(self.save_gui_settings)

        self.button_acquire = self.grid_top.place_object(_g.Button('Acquire',True).disable())
        self.label_dmm_name = self.grid_top.place_object(_g.Label('Disconnected'))

        self.settings  = self.grid_bot.place_object(_g.TreeDictionary(autosettings_path+'_settings.txt')).set_width(250)
        self.tabs_data = self.grid_bot.place_object(_g.TabArea(autosettings_path+'_tabs_data.txt'), alignment=0)
        self.tab_raw   = self.tabs_data.add_tab('Raw Data')

        self.label_path = self.tab_raw.add(_g.Label('Output Path:').set_colors('cyan' if _s.settings['dark_theme_qt'] else 'blue'))
        self.tab_raw.new_autorow()

        self.plot_raw  = self.tab_raw.place_object(_g.DataboxPlot('*.csv', autosettings_path+'_plot_raw.txt', autoscript=2), alignment=0)

        # Create a resource management object to populate the list
        if _mp._visa:
            if pyvisa_py: self.resource_manager = _mp._visa.ResourceManager('@py')
            else:         self.resource_manager = _mp._visa.ResourceManager()
        else: self.resource_manager = None

        # Populate the list.
        names = []
        if self.resource_manager:
            for x in self.resource_manager.list_resources():
                if self.resource_manager.resource_info(x).alias:
                    names.append(str(self.resource_manager.resource_info(x).alias))
                else:
                    names.append(x)

        # VISA settings
        self.settings.add_parameter('VISA/Device', 0, type='list', values=['Simulation']+names)

        # Acquisition settings
        self.settings.add_parameter('Acquire/Unlock', True, tip='Unlock the device\'s front panel after acquisition.')

        # Connect all the signals
        self.button_connect.signal_clicked.connect(self._button_connect_clicked)
        self.button_acquire.signal_clicked.connect(self._button_acquire_clicked)

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=autosettings_path)
        self._autosettings_controls = ['self.buttons[0]', 'self.buttons[1]',
                                       'self.buttons[2]', 'self.buttons[3]',
                                       'self.buttons[4]', 'self.buttons[5]',
                                       'self.buttons[6]', 'self.buttons[7]']
        self.load_gui_settings()

        # Show the window.
        self.window.show(block)

    def _button_connect_clicked(self, *a):
        """
        Connects or disconnects the VISA resource.
        """

        # If we're supposed to connect
        if self.button_connect.get_value():

            # Close it if it exists for some reason
            if not self.api == None: self.api.close()

            # Make the new one
            self.api = keithley_dmm_api(self.settings['VISA/Device'], self._pyvisa_py)

            # Tell the user what dmm is connected
            if self.api.instrument == None:
                self.label_dmm_name.set_text('*** Simulation Mode ***')
                self.label_dmm_name.set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
                self.button_connect.set_colors(background='pink')
            else:
                self.label_dmm_name.set_text(self.api.model)
                self.label_dmm_name.set_style('')
                self.button_connect.set_colors(background='')

            # Enable the Acquire button
            self.button_acquire.enable()

        elif not self.api == None:

            # Close down the instrument
            if not self.api.instrument == None:
                self.api.close()
            self.api = None
            self.label_dmm_name.set_text('Disconnected')

            # Make sure it's not still red.
            self.label_dmm_name.set_style('')
            self.button_connect.set_colors(background='')

            # Disable the acquire button
            self.button_acquire.disable()

    def _button_acquire_clicked(self, *a):
        """
        Get the enabled curves, storing them in plot_raw.
        """
        _debug('_button_acquire_clicked()')

        # Don't double-loop!
        if not self.button_acquire.is_checked(): return

        # Don't proceed if we have no connection
        if self.api == None:
            self.button_acquire.set_checked(False)
            return

        # Ask the user for the dump file
        self.path = _s.dialogs.save('*.csv', 'Select an output file.', force_extension='*.csv')
        if self.path == None: return

        # Update the label
        self.label_path.set_text('Output Path: ' + self.path)

        _debug('  path='+repr(self.path))

        # Disable the connection button
        self._set_acquisition_mode(True)

        # For easy coding
        d = self.plot_raw

        # Set up the databox columns
        _debug('  setting up databox')
        d.clear()
        for n in range(len(self.buttons)):
            if self.buttons[n].is_checked():
                d['t'+str(n+1)] = []
                d['v'+str(n+1)] = []

        # Reset the clock and record it as header
        self.api._t0 = _t.time()
        self._dump(['Date:', _t.ctime()], 'w')
        self._dump(['Time:', self.api._t0])

        # And the column labels!
        self._dump(self.plot_raw.ckeys)

        # Loop until the user quits
        _debug('  starting the loop')
        while self.button_acquire.is_checked():

            # Next line of data
            data = []

            # Get all the voltages we're supposed to
            for n in range(len(self.buttons)):

                # If the button is enabled, get the time and voltage
                if self.buttons[n].is_checked():

                    _debug('    getting the voltage')

                    # Get the time and voltage, updating the window in between commands
                    t, v = self.api.get_voltage(n+1, self.window.process_events)

                    # Append the new data points
                    d['t'+str(n+1)] = _n.append(d['t'+str(n+1)], t)
                    d['v'+str(n+1)] = _n.append(d['v'+str(n+1)], v)

                    # Update the plot
                    self.plot_raw.plot()
                    self.window.process_events()

                    # Append this to the list
                    data = data + [t,v]

            # Write the line to the dump file
            self._dump(data)

        _debug('  Loop complete!')

        # Unlock the front panel if we're supposed to
        if self.settings['Acquire/Unlock']: self.api.unlock()

        # Re-enable the connect button
        self._set_acquisition_mode(False)

    def _dump(self, a, mode='a'):
        """
        Opens self.path, writes the list a, closes self.path. mode is the file
        open mode.
        """
        _debug('_dump('+str(a)+', '+ repr(mode)+')')

        # Make sure everything is a string
        for n in range(len(a)): a[n] = str(a[n])
        self.a = a
        # Write it.
        f = open(self.path, mode)
        f.write(','.join(a)+'\n')
        f.close()

    def _set_acquisition_mode(self, mode=True):
        """
        Enables / disables the appropriate buttons, depending on the mode.
        """
        _debug('_set_acquisition_mode('+repr(mode)+')')
        self.button_connect.disable(mode)
        for b in self.buttons: b.disable(mode)

    def event_close(self, *a):
        """
        Quits acquisition loop when the window closes.
        """
        self.button_acquire.set_checked(False)







############################
# Example code
############################

if __name__ == '__main__':

    # self = adalm2000()
    # self.button_connect.click()
    #t = self.tabs.pop_tab(1)
    # self.ao.more.enableChannel(0, True)
    # self.ao.more.enableChannel(1, True)

    # s = self.tab_ai.settings

    #a = adalm2000()

    k = keithley_dmm()
