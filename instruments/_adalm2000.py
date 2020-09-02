# TO DO:
    # Write a baseline test script for the set_trigger_conditions() in external Ch2
    # _ai_settings_changed: Hide/show irrelevant trigger entries and the trigger level cursors in TI mode.

# NOTE: See gui_tools rather than copying code from here. A lot of the general
# device-indepenedent functionality lives there, and was used in soundcard.py.

import time      as _t
import numpy     as _n
import mcphysics as _mp
import spinmob   as _s
import spinmob.egg as _egg
_g = _egg.gui
try: from . import _gui_tools as _gt
except: _gt = _mp.instruments._gui_tools

import traceback as _traceback
_p = _traceback.print_last



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
            t.setAnalogCondition        (0, condition1)
            t.setAnalogExternalCondition(0, condition1)
            t.setAnalogCondition        (1, condition2)
            t.setAnalogExternalCondition(1, condition2) # BUG? This seems not to have any effect.

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
        if not self.simulation_mode:
            self.more.push([V1, V2])
        return self

    def zero(self):
        """
        Zero it. Stopping gives strange results. Disabling doesn't have an effect.
        """
        if not self.simulation_mode:
            self.set_enabled(True, True)
            self.send_samples_dual(_n.zeros(4), _n.zeros(4))

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
    name='adalm2000' : str
        Optional identifier for this instance of adalm2000 (in case you build
        a gui with many instances), used primarily for the remembering settings.
        Could be "Carl" for example.
    show=True : bool
        Whether to show the window upon creation.
    block=False : bool
        Whether to block the console when showing the window.
    """
    def __init__(self, name='adalm2000', show=True, block=False):

        self.timer_exceptions = _g.TimerExceptions()

        if _mp._libm2k == None: _s._warn('You need to install libm2k to access the adalm2000s.')

        # Remember the name
        self.name = name

        # Build the graphical user interface
        self._build_gui(block)

        # If we're supposed to show the window.
        if show: self.window.show(block)


    def _event_window_close(self, *a):
        """
        Called when the main window closes. Just stop the acquisition loops.
        """
        print('Shutting down acquisition and hiding window. Use self.window.show() to bring it back.')
        self._shut_down()

    def _shut_down(self):
        """
        Shuts off acquisitions and other loops, turns off outputs.
        """
        self.tab_ai.button_acquire.set_checked(False)
        self.waveform_designer.button_stop.click()
        self.quadratures.button_sweep.set_checked(False)
        self.tab_power.button_enable_Vm.set_checked(False)
        self.tab_power.button_enable_Vp.set_checked(False)

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
        self._build_tab_quad()
        self._build_tab_power()

        # Connect remaining signals
        self.button_connect.signal_toggled.connect(self._button_connect_toggled)

        # Disable the tabs until we connect
        self.tabs.disable()

        # Let's see it!
        self.window.event_close = self._event_window_close


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
        self.tab_power.button_enable_Vp  .signal_toggled.connect(self._power_settings_changed)
        self.tab_power.button_enable_Vm  .signal_toggled.connect(self._power_settings_changed)

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
        s = self.tab_ai.settings  = self.tab_ai.tab_controls.add(_g.TreeDictionary(
            autosettings_path = self.name+'.tab_ai.settings',
            name              = self.name+'.tab_ai.settings').set_width(230), column_span=4)
        s.add_parameter('Iterations', 0, tip='How many acquisitions to perform.')
        s.add_parameter('Samples', 1000.0, bounds=(2,None), siPrefix=True, suffix='S', dec=True, tip='How many samples to acquire. 1-8192 guaranteed. \nLarger values possible, depending on USB bandwidth.')
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
            ], tip='Which trigger event to send to the trigger out (TO) port.')

        s.add_parameter('Trigger/Delay', 0.0, suffix='s', siPrefix=True, step=0.01,
                        tip='Horizontal (time) offset relative to trigger point. The trigger point is always defined to be at time t=0.')

        s.add_parameter('Trigger/Ch1', [
            'Immediate',
            'Analog',
            'External (TI)',
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
            'External (TI)',
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
        self.tab_ai.button_acquire.signal_toggled.connect(self._ai_button_acquire_toggled)
        self.tab_ai.settings.connect_signal_changed('Trigger/Ch1/Level', self._ai_settings_changed)
        self.tab_ai.settings.connect_signal_changed('Trigger/Ch2/Level', self._ai_settings_changed)
        self.tab_ai.settings.connect_signal_changed('Trigger/Delay', self._ai_settings_changed)
        self.tab_ai.button_auto.signal_clicked.connect(self._ai_button_auto_clicked)

        # Trigger cursors
        self.tab_ai.plot_raw.ROIs[0][0].sigPositionChanged.connect(self._ai_cursor_drag)
        self.tab_ai.plot_raw.ROIs[1][0].sigPositionChanged.connect(self._ai_cursor_drag)
        self.tab_ai.plot_raw.ROIs[0][1].sigPositionChanged.connect(self._ai_cursor_drag)
        self.tab_ai.plot_raw.ROIs[1][1].sigPositionChanged.connect(self._ai_cursor_drag)

    def get_ao_rate(self, channel='Ch1'):
        """
        Gets the rate for the supplied output channel.
        """
        return self._ao_rates[self.waveform_designer.settings.get_list_index(channel+'/Rate')]

    def _build_tab_ao(self, ao_rates=[75e6, 75e5, 75e4, 75e3, 75e2, 75e1]):
        """
        Assembles the analog out tab.
        """
        self._ao_rates = ao_rates

        # DAC Tab
        self.tab_ao =self.tabs.add_tab('Analog Out')

        wd = self.waveform_designer = self.tab_ao.add(_gt.waveform_designer(
            rates = ['75 MHz', '7.5 MHz', '750 kHz', '75 kHz', '7.5 kHz', '750 Hz'],
            name = self.name+'.waveform_designer',
            sync_rates=False,
            sync_samples=False,
            buffer_increment=4,
            get_rate = self.get_ao_rate), alignment=0)
        self.waveform_designer.add_channels('Ch1','Ch2')

        to = self.tab_ao
        to.settings = wd.settings

        wd.tab_sent  = wd.tabs_plots.add_tab('Last Sent Waveform')
        wd.plot_sent = wd.tab_sent.add(_g.DataboxPlot(
            '*.w', autosettings_path=self.name+'.waveform_designer.plot_sent',
            autoscript=2), alignment=0)
        wd.plot_design = wd.plot_design

        wd.grid_controls = wd.tab_settings.add(_g.GridLayout(margins=False), 0,0, alignment=0)

        wd.button_send = wd.grid_controls.add(_g.Button(
            'Send', checkable=True,
            signal_clicked=self._ao_button_send_clicked,
            tip='Send the designed waveform to the actual analog outputs.'))

        wd.checkbox_auto = wd.grid_controls.add(_g.CheckBox(
            'Auto', autosettings_path=self.name+'.tab_ao.checkbox_auto',
            signal_toggled=self._ao_after_settings_changed,
            tip='Automatically send the designed waveform whenever it changes.'))

        wd.button_stop = wd.grid_controls.add(_g.Button(
            'Stop',
            signal_clicked=self._ao_button_stop_clicked,
            tip='Stop the output and set it to zero.'))

        wd.after_settings_changed = self._ao_after_settings_changed

    def _build_tab_quad(self):
        """
        Populates the lockin tab.
        """
        self.tab_quadratures = tl = self.tabs.add_tab('Quadratures')

        self.quadratures = tl.quadratures = tl.add(_gt.quadratures(
            channels=['Ch1','Ch2'], name=self.name+'.quadratures'), alignment=0)

        s = self.quadratures.settings

        s.add_parameter(
            'Output/Rate',
            ['75 MHz', '7.5 MHz', '750 kHz', '75 kHz', '7.5 kHz', '750 Hz', 'Automatic'],
            default_list_index=6, dec=True, suffix='S', siPrefix=True,
            tip='Maximum allowed input buffer, to prevent some crazy computer freeze.')

        # Add the "Go" button
        self.quadratures.button_go = self.quadratures.grid_left_top.add(_g.Button(
            text='Go', checkable=True,
            tip='Set up the outputs and inputs, collect data, and get the quadratures.',
            signal_toggled=self._quad_button_go_toggled).set_width(50), 0,1, alignment=2)

        # Overload the existing dummy function
        self.quadratures.get_raw = self._quad_get_raw

        # Not needed with auto checkbox.
        self.quadratures.button_loop.hide()

        # Link other signals to functions
        self.quadratures.button_sweep.signal_toggled.connect(self._quad_button_sweep_toggled)
        self.quadratures.number_step.signal_changed.connect(self._quad_number_step_changed)
        self.quadratures.number_frequency.signal_changed.connect(self._quad_number_frequency_changed)
        # Signal for when it's time to send data to the quad
        #self.quadratures.signal_new_data = _s.thread.signal(self._quad_got_new_data)


    # def demodulate(self, f=None):
    #     """
    #     Perform a demodulation of both Analog input channels at the specified
    #     frequency f.

    #     Parameters
    #     ----------
    #     f=None : float
    #         Frequency at which to perform the demodulation. If f=None, this will
    #         use the current value in self.quadratures.number_frequency.

    #     Returns
    #     -------
    #     self
    #     """
    #     # Get or set the demod frequency.
    #     if f==None: f = self.quadratures.number_frequency.get_value()
    #     else:           self.quadratures.number_frequency.set_value(f)

    #     # Get the source databox and demod plotter
    #     d = self.tab_ai.plot_raw
    #     p = self.tab_quadratures.plot

    #     # Get the time axis and the two quadratures
    #     t = d[0]
    #     X = _n.cos(2*_n.pi*f*t)
    #     Y = _n.sin(2*_n.pi*f*t)

    #     # Normalize
    #     X = _n.nan_to_num(X/sum(X*X))
    #     Y = _n.nan_to_num(Y/sum(Y*Y))

    #     # Demodulate
    #     V1X = sum(d['V1']*X)
    #     V1Y = sum(d['V1']*Y)
    #     V2X = sum(d['V2']*X)
    #     V2Y = sum(d['V2']*Y)

    #     # Get the next index
    #     if not len(p): n = 0
    #     else:          n = len(p[0])

    #     # Append to the demodder
    #     p.append_row([n, f, V1X, V1Y, V2X, V2Y], ['n', 'f', 'V1X', 'V1Y', 'V2X', 'V2Y'])

    #     # Update the header
    #     d.copy_headers_to(p)
    #     self.tab_ao.settings.send_to_databox_header(p)
    #     self.tab_quadratures.settings.send_to_databox_header(p)

    #     # Plot!
    #     p.plot()
    def _quad_get_raw(self, *a):
        """
        Overloads the get_raw() function in the gui_tools. Just imports the data
        from the AI tab.
        """
        # Get data
        # Shortcuts
        pd = self.quadratures.plot_raw
        pr = self.tab_ai.plot_raw

        # Clear and import the header
        pd.clear()
        pd.copy_headers_from(pr)

        # Copy the columns in the right fashion (time-signal pairs)
        for k in pr.ckeys[1:]:
            pd['t_'+k] = pr['t']
            pd[k]  = pr[k]

        pd.plot().autosave()

    def _quad_number_step_changed(self, *a):
        """
        Updates the frequency
        """
        q = self.quadratures
        q.number_frequency(q.get_sweep_step_frequency(q.number_step()))

    def _quad_number_frequency_changed(self, *a):
        """
        Updates the waveform designer and input.
        """
        self._quad_configure_ao_ai()

    def _quad_button_go_toggled(self, *a):
        """
        Take single demodulations for the specified iterations, without stepping frequency.
        Appends them to the LI Demodulation plot.
        """
        q = self.quadratures

        # If we just turned it off, poop out instead of starting another loop.
        if not q.button_go.is_checked(): return

        # Reset the button colors (they turn red when it's not locked / triggered)
        q.button_go.set_colors('white', 'blue')

        # Enable demodulation analysis
        q.checkbox_auto.set_checked(True)

        # Configure the output and start the AO
        self._quad_configure_ao_ai()
        self.waveform_designer.button_send.click()

        # Wait for the send to finish
        while self.waveform_designer.button_send.is_checked(): self.window.sleep(0.01)

        # Settle into steady state.
        self.window.sleep(q.settings['Input/Settle'])

        # reset the counter
        I = q.number_iteration_sweep
        I(0)
        while I() < q.settings['Input/Iterations'] \
        and   q.button_go():
            I.increment()

            # Acquire
            self.tab_ai.button_acquire(True)
            while self.tab_ai.button_acquire(): self.window.sleep()
            self.window.process_events()

        q.button_go(False).set_colors(None, None)
        q.checkbox_auto(False)

    def _quad_button_sweep_toggled(self, *a):
        """
        Starts a sweep.
        """
        q  = self.quadratures

        # If we just unchecked it, let the loop poop itself out.
        if not q.button_sweep.is_checked(): return
        q.button_sweep.set_colors('white', 'green')

        # Shortcuts
        sq = q.settings
        S  = q.number_step

        # Don't throw away data!
        q.number_history(0)

        # Do the loop
        S(0)
        while S() < sq['Sweep/Steps'] and q.button_sweep():

            # Increment the step and frequency
            S.increment() # Updates the frequency
            self.window.process_events()

            # Go for this frequency!
            q.button_go.click()

        # Uncheck it when done
        q.button_sweep.set_checked(False)
        q.button_sweep.set_colors(None, None)

    def _quad_get_errthing_that_fits(self, cs):
        """
        cs is the channel to calculate for

        Returns the
        nearest frequency,
        number of cycles for this frequency,
        number of samples to generate it,
        the rate, and the rate's index.
        """
        so = self.waveform_designer.settings

        # Calculate lowest allowed rate
        ro, no = self._quad_get_output_rate_and_index()

        # Target period
        f_target = self.quadratures.number_frequency.get_value()

        # If zero, it's simple
        if not f_target: return f_target, 1, so[cs+'/Samples/Min'], ro, no

        # Now, given this rate, calculate the number of points needed to make one cycle.
        N1 = ro / f_target # This is a float with a remainder

        # The goal now is to add an integer number of these cycles up to the
        # Max_Buffer and look for the one with the smallest remainder.
        max_cycles = int(        so[cs+'/Samples/Max']/N1 )
        min_cycles = int(_n.ceil(so[cs+'/Samples/Min']/N1))

        # List of options to search
        options   = _n.array(range(min_cycles,max_cycles+1)) * N1 # Possible floats

        # How close each option is to an integer.
        residuals = _n.minimum(abs(options-_n.ceil(options)), abs(options-_n.floor(options)))

        # Now we can get the number of cycles
        c = _n.where(residuals==min(residuals))[0][0]

        # Now we can get the number of samples
        N = int(_n.round(N1*(c+min_cycles)))

        # If this is below the minimum value, set it to the minimum
        if N < so[cs+'/Samples/Min']: N = so[cs+'/Samples/Min']

        # Update the GUI
        #self.tab_quadratures.label_samples.set_text('AO Buffer: '+str(N))

        # Now, given this number of points, which might include several oscillations,
        # calculate the actual closest frequency
        df = ro/N # Frequency step
        n  = int(_n.round(self.quadratures.number_frequency()/df)) # Number of cycles
        f  = n*df # Actual frequency that fits.

        return f, n, N, ro, no

    def _quad_configure_ao_ai(self):
        """
        Configures the output and input for lock-in, choosing the highest frequency
        possible, given the maximum input buffer.
        """
        ### Remember the settings

        # Shortcuts
        si = self.tab_ai.settings
        so = self.waveform_designer.settings
        q = self.quadratures
        sq = q.settings

        ### Set up the AO. We "intelligently" choose the output rate to get
        # Disable auto waveform update.
        self.waveform_designer.checkbox_auto.set_checked(False)

        # close to the desired frequency
        rate_index = self._quad_get_best_ao_rate_index('Ch1', q.number_frequency())

        # Set up the output channels
        d = dict()
        for c in ['Ch1','Ch2']:
            d[c+'/Waveform']       = 'Sine'
            d[c+'/Sine/Amplitude'] = sq['Output/'+c+'_Amplitude']
            d[c+'/Sine/Offset']    = 0
            d[c+'/Sine/Phase']     = 90

            so.update(d, block_key_signals=True)
            so.set_list_index(c+'/Rate', rate_index, block_key_signals=True)
            so.set_value(c+'/Sine', self.quadratures.number_frequency(), block_key_signals=True)

            # Update the actual frequency etc
            self.waveform_designer.update_other_quantities_based_on(c+'/Sine')

        self.waveform_designer.update_design()
        f = so['Ch1/Sine']

        ### Set up the AI tab.

        # Set the rates to match and get the input rate
        si.set_list_index('Rate', rate_index)
        ri = self._ai_get_rate()

        # Calculate how many samples to record after the delay
        # If f is nonzero, we need an integer number of cycles * time per cycle * the rate
        if f:
            samples = _n.ceil(sq['Input/Collect']*f) / f * ri

            # If we have too many samples, calculate the max possible within bounds
            if samples > sq['Input/Max_Samples']:
                samples = _n.round(_n.floor(sq['Input/Max_Samples']*f)/f)

                # If we got a zero back, we can't even fit one period in the
                # input buffer. We should never get here, but raise a flag!
                if samples <= 0:
                    print('ERROR: Max input buffer cannot hold even a single period!')
                    self.window.set_colors(None, 'pink')
                    samples = sq['Input/Max_Samples']

        # Otherwise, we just use the time.
        else: samples = min(sq['Input/Max_Samples'], _n.round(sq['Sweep/Collect'] * ri))

        # Finally.
        si['Samples'] = samples

        # Set the timeout to something reasonable
        si['Timeout'] = max(5*(si['Samples']/ri + si['Trigger/Delay']), 1)

        # Other settings
        si['Iterations']    = 1
        si['Trigger/In']    = 'Ch1'
        si['Trigger/Ch1']   = 'Immediate'
        si['Trigger/Delay'] = 0 # We manually delay.

        # Also update the demod frequency
        self.quadratures.number_frequency(f, block_signals=True)

        # Make sure everything updates!
        self.window.process_events()

    def _quad_get_best_ao_rate_index(self, channel, f_target, min_samples_per_period=20):
        """
        Returns the rate and index of the best rate for the specified
        channel and target frequency, respecting the buffer mins and maxes.

        We get the minimum rate, because that allows for the finest frequency
        resolution.

        min_samples_per_period is the minimum number of cycles per period.
        """
        sq = self.quadratures.settings

        if sq['Output/Rate'] == 'Automatic':

            # Minimum rate
            if f_target: rate_min = min_samples_per_period*f_target
            else:        rate_min = sq['Input/Max_Samples']/sq['Sweep/Collect']

            # Now find the first rate higher than this
            for n in range(len(self._ao_rates)):
                r = self._ao_rates[-n-1]
                if r > rate_min: break

            # Now get the actual frequency associated with this number of steps
            return self._ao_rates.index(r)

        # Rate is specified by the user
        else: return sq.get_list_index('Output/Rate')

    def _ao_button_stop_clicked(self, *a):
        """
        Stop the ao.
        """
        if hasattr(self, 'ao'): self.ao.zero()

    def _ao_button_send_clicked(self, *a):
        """
        Sends the current design waveform to
        """
        if not self.waveform_designer.button_send.is_checked(): return
        self.window.process_events()

        s = self.waveform_designer.settings
        p = self.waveform_designer.plot_design

        # Enable / disable outputs
        self.ao.set_enabled(s['Ch1'], s['Ch2'])

        # Set the rates
        self.ao.set_sample_rates(self._ao_get_rate('Ch1'), self._ao_get_rate('Ch2'))

        # Set Loop mode (BUG: NEED TO DO THIS TWICE FOR IT TO STICK)
        self.ao.set_loop_modes(s['Ch1/Loop'], s['Ch2/Loop'])
        self.ao.set_loop_modes(s['Ch1/Loop'], s['Ch2/Loop'])

        # Dual sync'd mode
        if s['Ch1'] and s['Ch2']: self.ao.send_samples_dual(p['Ch1'], p['Ch2'])

        # Individual channel basis
        else:
            if s['Ch1']: self.ao.send_samples(1, p['Ch1'])
            if s['Ch2']: self.ao.send_samples(2, p['Ch2'])

        # Clear and replace the send plot info
        ps = self.waveform_designer.plot_sent
        ps.clear()
        ps.copy_all(p)
        ps.plot(); self.window.process_events()

        self.waveform_designer.button_send.set_checked(False)
        self.window.process_events()

    def _ao_after_plot_design_load(self):
        """
        Do stuff after the plot is loaded. Update sample rate, samples, switch
        to custom mode, etc.
        """
        s = self.waveform_designer.settings
        p = self.waveform_designer.plot_design
        s.update(p)

    def _ao_get_rate(self, c):
        """
        Returns the rate for the specified channel ('Ch1', or 'Ch2').
        """
        return self._ao_rates[self.waveform_designer.settings.get_list_index(c+'/Rate')]

    def _ao_update_waveform_frequency(self, c, w):
        """
        Returns the frequency for the settings under the specified root (e.g. c='Ch1', w='Sine')
        """
        s = self.waveform_designer.settings
        s.set_value(c+'/'+w, self._ao_get_rate(c)/s[c+'/Samples']*s[c+'/'+w+'/Cycles'],
            block_all_signals=True)

    # def _ao_settings_add_channel(self, c):
    #     """
    #     Adds everything for the specified channel ('Ch1' or 'Ch2') to the tab_ao.settings.
    #     """
    #     s = self.waveform_designer.settings

    #     s.add_parameter(c, True, tip='Enable analog output 1')
    #     s.add_parameter(c+'/Rate', ['75 MHz', '7.5 MHz', '750 kHz', '75 kHz', '7.5 kHz', '750 Hz'], tip='How fast to output voltages.')
    #     s.add_parameter(c+'/Samples',  8000, bounds=(1,None), dec=True, suffix='S', siPrefix=True, tip='Number of samples in the waveform. Above 8192, this number depends on USB bandwidth, I think.')
    #     s.add_parameter(c+'/Loop', True, tip='Whether the waveform should loop.')
    #     s.add_parameter(c+'/Waveform', ['Sine', 'Square', 'Pulse_Decay', 'Custom'], tip='Choose a waveform.')

    #     # Sine
    #     s.add_parameter(c+'/Sine',           0.0, suffix='Hz', siPrefix=True, tip='Frequency (from settings below).', readonly=True)
    #     s.add_parameter(c+'/Sine/Cycles',      1, dec=True, tip='How many times to repeat the waveform within the specified number of samples.' )
    #     s.add_parameter(c+'/Sine/Amplitude', 0.1, suffix='V', siPrefix=True, tip='Amplitude (not peak-to-peak).')
    #     s.add_parameter(c+'/Sine/Offset',    0.0, suffix='V', siPrefix=True, tip='Offset.')
    #     s.add_parameter(c+'/Sine/Phase',     0.0, step=5, suffix=' deg', tip='Phase of sine (90 corresponds to cosine).')

    #     # Square
    #     s.add_parameter(c+'/Square',       0.0, suffix='Hz', siPrefix=True, tip='Frequency (from settings below).', readonly=True)
    #     s.add_parameter(c+'/Square/Cycles',  1, dec=True, tip='How many times to repeat the waveform within the specified number of samples.' )
    #     s.add_parameter(c+'/Square/High',  0.1, suffix='V', siPrefix=True, tip='High value.')
    #     s.add_parameter(c+'/Square/Low',   0.0, suffix='V', siPrefix=True, tip='Low value.')
    #     s.add_parameter(c+'/Square/Start', 0.0, step=0.01, bounds=(0,1), tip='Fractional position within a cycle where the voltage goes high.')
    #     s.add_parameter(c+'/Square/Width', 0.5, step=0.01, bounds=(0,1), tip='Fractional width of square pulse within a cycle.')

    #     # Square
    #     s.add_parameter(c+'/Pulse_Decay/Amplitude',  0.1,   suffix='V',  siPrefix=True, tip='Pulse amplitude.')
    #     s.add_parameter(c+'/Pulse_Decay/Offset',     0.0,   suffix='V',  siPrefix=True, tip='Baseline offset.')
    #     s.add_parameter(c+'/Pulse_Decay/Tau',        10e-6, suffix='s',  siPrefix=True, dec=True, tip='Exponential decay time constant.')
    #     s.add_parameter(c+'/Pulse_Decay/Zero',       False, tip='Whether to zero the output voltage at the end of the pulse.')

    def _ao_after_settings_changed(self, *a):
        """
        When someone changes the ao settings, update the waveform.
        """
        if self.waveform_designer.checkbox_auto(): self.waveform_designer.button_send.click()

    # def _ao_settings_select_waveform(self, c):
    #     """
    #     Shows and hides the waveform menus based on the selected value.
    #     c = 'Ch1' or 'Ch2'.
    #     """
    #     # Show and hide waveform designers
    #     s = self.waveform_designer.settings
    #     for w in ['Sine', 'Square', 'Pulse_Decay']: s.hide_parameter(c+'/'+w, w == s[c+'/Waveform'])

    # def _ao_update_design(self):
    #     """
    #     Updates the design waveform based on the current settings.
    #     """
    #     s = self.waveform_designer.settings

    #     # Calculate the frequencies from the Repetitions etc
    #     for w in ['Sine', 'Square']:
    #         self._ao_update_waveform_frequency('Ch1', w)
    #         self._ao_update_waveform_frequency('Ch2', w)

    #     # Overwrite what's in there.
    #     p = self.waveform_designer.plot_design
    #     s.send_to_databox_header(p)
    #     self._ao_generate_waveform('Ch1')
    #     self._ao_generate_waveform('Ch2')

    #     # Plot it
    #     p.plot(); self.window.process_events()

    # def _ao_generate_waveform(self, c):
    #     """
    #     Generates the waveform in settings channel c (can be 'Ch1' or 'Ch2'), and
    #     sends this to the design plotter.
    #     """
    #     s = self.waveform_designer.settings    # Shortcut to settings
    #     p = self.waveform_designer.plot_design # Shortcut to plotter
    #     w = s[c+'/Waveform']        # Waveform string, e.g. 'Sine'
    #     N = s[c+'/Samples']         # Number of samples
    #     R = self._ao_get_rate(c)    # Sampling rate in Hz

    #     # Get the time array
    #     t = p['t'+c[-1]] = _n.linspace(0,(N-1)/R,N)

    #     # Don't adjust the voltages if custom mode unless the lengths don't match
    #     if w == 'Custom':
    #         if not len(t) == len(p['V'+c[-1]]): p['V'+c[-1]] = _n.zeros(len(t))
    #         return

    #     # Get the frequency and period for the other modes
    #     if w in ['Sine', 'Square']:
    #         f = s[c+'/'+w]              # Frequency in Hz
    #         T = 1.0/f                   # Period (sec)

    #     # Get the waveform
    #     if   w == 'Sine': p['V'+c[-1]] = s[c+'/Sine/Offset'] + s[c+'/Sine/Amplitude']*_n.sin((2*_n.pi*f)*t + s[c+'/Sine/Phase']*_n.pi/180.0)
    #     elif w == 'Square':

    #         # Start with the "low" values
    #         v = _n.full(N, s[c+'/Square/Low'])

    #         # Get the pulse up and down times for one cycle
    #         t1 = T*s[c+'/Square/Start']
    #         t2 = T*s[c+'/Square/Width'] + t1

    #         # Loop over the segments adding "high" values
    #         for n in range(s[c+'/Square/Cycles']):

    #             # Start of cycle
    #             t0 = n*T

    #             # Set the high value for this cycle
    #             v[_n.logical_and(t>=t0+t1, t<t0+t2)] = s[c+'/Square/High']

    #         # Set it
    #         p['V'+c[-1]] = v

    #     elif w == 'Pulse_Decay':
    #         p['V'+c[-1]] = s[c+'/Pulse_Decay/Offset'] + s[c+'/Pulse_Decay/Amplitude']*_n.exp(-t/s[c+'/Pulse_Decay/Tau'])
    #         if s[c+'/Pulse_Decay/Zero']:
    #             p['V'+c[-1]][-1] = 0





    def _button_connect_toggled(self, *a):
        """
        Called when someone clicks the "connect" button.
        """
        if self.button_connect.is_checked():

            # Get the adalm2000's URI
            uri = self.combo_contexts.get_text()
            self.combo_contexts.disable()
            self.button_connect.set_colors('white', '#004455')

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
                self.label_status.set_colors('cyan' if _s.settings['dark_theme_qt'] else 'blue')

            # Enable the tabs.
            self.tabs.enable()

            # Reset the power supply
            self._power_settings_changed()

            # Start the timer
            self.tab_power.timer.start()
            self.t0 = _t.time()

        # Otherwise, shut down
        else:
            self._shut_down()
            self.tabs.disable()
            self.button_connect.set_colors()
            self.combo_contexts.enable()

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
        tp = self.tab_power
        if tp.button_enable_Vp():
            Vp = tp.number_set_Vp()
            tp.button_enable_Vp.set_colors('white', 'green')
        else:
            Vp = 0
            tp.button_enable_Vp.set_colors(None, None)

        if tp.button_enable_Vm():
            Vm = tp.number_set_Vm()
            tp.button_enable_Vm.set_colors('white', 'green')
        else:
            Vm = 0
            tp.button_enable_Vm.set_colors(None, None)

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

    def _ai_button_acquire_toggled(self, *a):
        """
        Called when someone clicks the "acquire" button on the ADC tab.
        """
        # If we just turned it off, poop out instead of starting another loop.
        if not self.tab_ai.button_acquire.is_checked(): return

        self.tab_ai.button_acquire.set_colors('white', 'blue')

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

            # BUG WORKAROUND: set_trigger_conditions() doesn't seem to work for Ch2 External.
            if s['Trigger/In'] == 'Ch2' and s['Trigger/Ch2'] == 'External (TI)':
                s['Trigger/In'] = 'Ch1'
                s['Trigger/Ch1'] = 'External (TI)'

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
            ts = _n.linspace(t_delay, t_delay + (int(s['Samples'])-1)/rate, int(s['Samples']))

            # Get the data
            self.tab_ai.button_onair(True).set_colors('red', 'pink');
            self.window.process_events();

            vs = self.ai.get_samples(int(s['Samples']))

            self.tab_ai.button_onair(False).set_colors(None, None);
            self.window.process_events();

            # If vs==None it's a timeout
            if vs:
                # Clear and send the current settings to plotter
                p.clear()
                s.send_to_databox_header(p)
                self.waveform_designer.settings.send_to_databox_header(p)
                self.quadratures.settings.send_to_databox_header(p)
                p.h(t=_t.time()-self.t0, t0=self.t0)

                # Add columns
                p['t'] = ts
                for i in range(len(vs)): p['V'+str(i+1)] = vs[i]

                # Update the plot and autosave if that's enabled
                p.plot()
                p.autosave()

                # External analysis
                self.process_data()

                # If quad is enabled, send it over and process it
                q = self.quadratures
                if q.checkbox_auto():

                    # Import the data
                    q.button_get_raw.click()
                    self.window.process_events()

                    # Get the quadratures
                    q.button_get_quadratures.click()
                    self.window.process_events()

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
                if self.quadratures.button_get_raw.is_checked():
                    self.quadratures.button_get_raw.set_colors('white', 'red')

            # Let the user interact
            self.window.process_events()

        # Pop the button when we're done.
        self.tab_ai.button_acquire(False).set_colors()

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




if __name__ == '__main__':
    _m = _mp._libm2k
    #_g.clear_egg_settings()
    self = adalm2000()
    self.button_connect.click()
