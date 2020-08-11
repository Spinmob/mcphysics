import os        as _os
import time      as _t
import numpy     as _n
import mcphysics as _mp
import spinmob   as _s
import spinmob.egg as _egg
_g = _egg.gui



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
        self.tab_ao.button_stop.click()
        self.tab_li.button_sweep.set_checked(False)
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
        self._build_tab_li()
        self._build_tab_power()

        # Connect remaining signals
        self.button_connect.signal_toggled.connect(self._button_connect_toggled)

        # Disable the tabs until we connect
        self.tabs.disable()

        # Let's see it!
        self.window.event_close = self._event_window_close
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
        tl.button_go.signal_toggled          .connect(self._li_button_go_toggled)
        tl.button_sweep.signal_toggled       .connect(self._li_button_sweep_toggled)

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

    def _li_button_go_toggled(self, *a):
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



    def _li_button_sweep_toggled(self, *a):
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
            else:                    self.tab_li.plot.load_script(_os.path.join(_mp.__path__[0], 'plot_scripts', 'ADALM2000', 'li_sweep_magphase.py'))

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
        if hasattr(self, 'ao'): self.ao.zero()

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





    def _button_connect_toggled(self, *a):
        """
        Called when someone clicks the "connect" button.
        """
        if self.button_connect.is_checked():

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

    def _ai_button_acquire_toggled(self, *a):
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

