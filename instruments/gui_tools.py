import spinmob.egg as _egg
import spinmob     as _s
import numpy       as _n

# Shortcuts
_g = _egg.gui
_p = _s._p
_x = None



def get_nearest_frequency_settings(f_target=12345.678, rate=10e6, min_samples=200, max_samples=8096):
    """
    Finds the closest frequency (Hz) that is possible for the specified rate (Hz)
    and a buffer size between min_samples and max_samples.

    Parameters
    ----------
    f_target : float
        Target frequency (Hz)

    rate: float
        Sampling rate (Hz)

    min_samples : int
        Minimum buffer size allowed.

    max_samples : int
        Maximum buffer size allowed.

    Returns
    -------
    nearest achievable frequency

    number of full cycles within the buffer for this frequency

    buffer size to achieve this
    """

    # Now, given this rate, calculate the number of points needed to make one cycle.
    N1 = rate / f_target # This is a float with a remainder

    # The goal now is to add an integer number of these cycles up to the
    # max_samples and look for the one with the smallest remainder.
    max_cycles = int(        max_samples/N1 )
    min_cycles = int(_n.ceil(min_samples/N1))

    # List of options to search
    options = _n.array(range(min_cycles,max_cycles+1)) * N1 # Possible floats

    # How close each option is to an integer.
    residuals = _n.minimum(abs(options-_n.ceil(options)), abs(options-_n.floor(options)))

    # Now we can get the number of cycles
    c = _n.where(residuals==min(residuals))[0][0]

    # Now we can get the number of samples
    N = int(_n.round(N1*(c+min_cycles)))

    # If this is below the minimum value, set it to the minimum
    if N < min_samples: N = min_samples

    # Now, given this number of points, which might include several oscillations,
    # calculate the actual closest frequency
    df = rate/N # Frequency step
    n  = int(_n.round(f_target/df)) # Number of cycles
    f  = n*df # Actual frequency that fits.

    return f, n, N

class signal_chain(_g.Window):
    """
    Tab area containing a raw data tab and signal processing tabs.

    Parameters
    ----------
    name='signal_chain'
        Unique identifier for autosettings. Make sure it is unique!
    margins=False
        Whether to include margins around this.

    **kwargs are sent to the raw databox plot.
    """
    def __init__(self, name='signal_chain', margins=False, **kwargs):

        # Initialize the tabarea
        _g.Window.__init__(self, title=name, margins=margins, autosettings_path=name)
        self.tabs = self.add(_g.TabArea(autosettings_path=name+'.tabs'), alignment=0)

        # Remember this
        self.name = name

        # Add the tabs
        self.tab_raw = self.tabs.add_tab('Raw')
        self.tab_A1  = self.tabs.add_tab('A1')
        self.tab_A2  = self.tabs.add_tab('A2')
        self.tab_A3  = self.tabs.add_tab('A3')
        self.tab_B1  = self.tabs.add_tab('B1')
        self.tab_B2  = self.tabs.add_tab('B2')
        self.tab_B3  = self.tabs.add_tab('B3')

        # Add the raw plot
        self.plot_raw = self.tab_raw.add(_g.DataboxPlot('*.raw', autosettings_path=name+'.plot_raw'), alignment=0)

        # Add the anlaysers
        self.A1 = self.tab_A1.add(_g.DataboxProcessor(name=name+'.A1', databox_source=self.plot_raw, file_type='*.A1'), alignment=0)
        self.A2 = self.tab_A2.add(_g.DataboxProcessor(name=name+'.A2', databox_source=self.A1.plot,  file_type='*.A2'), alignment=0)
        self.A3 = self.tab_A3.add(_g.DataboxProcessor(name=name+'.A3', databox_source=self.A2.plot,  file_type='*.A3'), alignment=0)
        self.B1 = self.tab_B1.add(_g.DataboxProcessor(name=name+'.B1', databox_source=self.plot_raw, file_type='*.B1'), alignment=0)
        self.B2 = self.tab_B2.add(_g.DataboxProcessor(name=name+'.B2', databox_source=self.B1.plot,  file_type='*.B2'), alignment=0)
        self.B3 = self.tab_B3.add(_g.DataboxProcessor(name=name+'.B3', databox_source=self.B2.plot,  file_type='*.B3'), alignment=0)

    def process_data(self):
        """
        Runs the data processing chain on whatever data is in self.plot_raw.
        """
        # Speed optimization...
        if self.A1.settings['Enabled']:
            self.A1.run()
            if self.A2.settings['Enabled']:
                self.A2.run()
                if self.A3.settings['Enabled']:
                    self.B3.run()

        if self.B1.settings['Enabled']:
            self.B1.run()
            if self.B2.settings['Enabled']:
                self.B2.run()
                if self.B3.settings['Enabled']:
                    self.B3.run()
        return self

    run = process_data

class waveform_designer(_g.Window):
    """
    Base GUI for creating output waveforms.

    Parameters
    ----------
    channels=['Ch1','Ch2']
        Names of available channels.
    rates=1000
        Can be a list of available output rates (Hz, numbers or strings), or number (Hz).
        You are responsible for overloading self.get_rate if you use a list of strings!
    name='waveform_designer'
        Unique identifier for autosettings. Make sure it is unique!
    sync_rates=False
        Set to True to automatically synchronize the rates between channels.
    sync_samples=False
        Set to True to automatically synchronize the number of output samples between channels.
    margins=False
        Whether to include margins around this.

    **kwargs are sent to the waveform DataboxPlot.
    """
    def __init__(self, channels=['Ch1','Ch2'], rates=1000, name='waveform_designer', sync_rates=False, sync_samples=False, margins=False, **kwargs):
        _g.Window.__init__(self, title=name, margins=margins, autosettings_path=name)

        # Remember these specifications
        self.name=name
        self.sync_rates   = sync_rates
        self.sync_samples = sync_samples
        self._rates = rates
        self._channels = []


        # Settings tabs
        self.new_autorow()
        self.tabs_settings = self.add(_g.TabArea(autosettings_path=name+'.tabs_settings'))
        self.tab_settings  = self.tabs_settings.add_tab('Waveform Settings')
        self.tab_settings.new_autorow()
        self.settings      = self.tab_settings.add(_g.TreeDictionary(autosettings_path=name+'.settings', name=name+'.settings'))
        self.settings.set_width(250)

        # Plot tabs
        self.tabs_plots  = self.add(_g.TabArea(autosettings_path=name+'.tabs_plots'), alignment=0)
        self.tab_design  = self.tabs_plots.add_tab('Waveform Designer')
        self.tab_design.new_autorow()
        self.plot_design = self.tab_design.add(_g.DataboxPlot(file_type='*.w', autosettings_path=name+'.plot_design', autoscript=2, **kwargs), alignment=0)

    def _get_nearest_frequency_settings(self, key):
        """
        Finds the closest frequency possible for the current settings, then
        updates the value at this key. Assumes the frequency key is something like
        'Channel/Square'
        """
        channel = key.split('/')[-2]
        f, cycles, samples = get_nearest_frequency_settings(
            f_target    = self.settings[key],
            rate        = self.get_rate(channel),
            min_samples = self.settings[channel+'/Samples/Min'],
            max_samples = self.settings[channel+'/Samples/Max'])

        # Now update the settings
        self.settings[channel+'/Samples'] = samples
        self.settings[key+'/Cycles']      = cycles

    def _generate_waveform(self, channel='Ch1'):
        """
        Generates the waveform in settings channel, and
        sends this to the design plotter.
        """
        c = channel
        s = self.settings    # Shortcut to settings
        p = self.plot_design # Shortcut to plotter
        w = s[c+'/Waveform']        # Waveform string, e.g. 'Sine'
        N = int(s[c+'/Samples'])    # Number of samples
        R = self.get_rate(c)    # Sampling rate in Hz

        # Get the time array
        t = p['t_'+c] = _n.linspace(0,(N-1)/R,N)

        # Don't adjust the voltages if custom mode unless the lengths don't match
        if w == 'Custom':
            if not len(t) == len(p[c]): p[c] = _n.zeros(len(t))
            return

        # Get the frequency and period for generating the other waveforms
        if w in ['Sine', 'Square']:
            f = s[c+'/'+w]              # Frequency in Hz
            if f: T = 1.0/f             # Period (sec)
            else: T = 0

        # Get the waveform
        if   w == 'Sine':
            p[c] = s[c+'/Sine/Offset'] + s[c+'/Sine/Amplitude']*_n.sin((2*_n.pi*f)*t + s[c+'/Sine/Phase']*_n.pi/180.0)

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
            p[c] = v

        elif w == 'Pulse_Decay':
            p[c] = s[c+'/Pulse_Decay/Offset'] + s[c+'/Pulse_Decay/Amplitude']*_n.exp(-t/s[c+'/Pulse_Decay/Tau'])
            if s[c+'/Pulse_Decay/Zero']:
                p[c][-1] = 0

    def _settings_changed(self, *a):
        """
        When someone changes the ao settings, update the waveform.
        """
        if len(a):
            name = a[0].name()
            key = self.settings.get_full_key(a[0])

            # Update the other quantities for this channel
            self._sync_rates_samples_time(key)

            # Sync the other settings if we're supposed to.
            if name in ['Rate', 'Samples', 'Time']:
                self._sync_channels(a[0].parent().name())

            # If it's a frequency, we have to calculate the closest possible
            elif name in ['Sine', 'Square']: self._get_nearest_frequency_settings(key)



        # Select the appropriate waveform
        for c in self._channels: self._settings_select_waveform(c)

        # Update the other parameters and generate waveforms
        self._update_design()

        # After settings changed
        self.after_settings_changed(*a)

    def _settings_select_waveform(self, channel='Ch1'):
        """
        Shows and hides the waveform menus based on the selected value.
        """
        # Show and hide waveform designers
        s = self.settings
        for w in self._waveforms:
            s.hide_parameter(channel+'/'+w, w == s[channel+'/Waveform'])

    def _sync_rates_samples_time(self, key):
        """
        Syncs the Rate, Samples, and Time based on what changed.
        """
        x = key.split('/')

        # If we get a Rate, Samples, or Time, update the others
        if x[1] in ['Rate', 'Samples', 'Time']:
            s = self.settings

            # If Rate or Time changed, set the number of samples, rounding
            if x[1] in ['Rate', 'Time']: s.set_value(x[0]+'/Samples', _n.ceil(s[x[0]+'/Time'] * self.get_rate(x[0])), block_key_signals=True)

            # Make sure the time matches the rounded samples (or changed samples!)
            s.set_value(x[0]+'/Time', s[x[0]+'/Samples'] / self.get_rate(x[0]), block_key_signals=True)


    def _sync_channels(self, channel):
        """
        Syncs them up if we're supposed to, using channel as the example.
        """

        # Synchronize the rates and samples
        for c in self._channels:

            # Only edit the OTHER channels
            if c != channel:

                # Sync the rates if we're supposed to
                if self.sync_rates:
                    self.settings.set_value(c+'/Rate',    self.settings[channel+'/Rate'], block_key_signals=True)

                # Sync the samples if we're supposed to
                if self.sync_samples:
                    self.settings.set_value(c+'/Samples', self.settings[channel+'/Samples'], block_key_signals=True)
                    self.settings.set_value(c+'/Time',    self.settings[channel+'/Time'],    block_key_signals=True)


    def _update_design(self):
        """
        Updates the design waveform based on the current settings.
        """
        s = self.settings

        # Overwrite what's in there.
        p = self.plot_design
        s.send_to_databox_header(p)

        # Calculate the frequencies from the Repetitions etc and generate the waveform data
        for w in ['Sine', 'Square']:
            for c in self._channels:
                self._update_waveform_frequency(c, w)
                self._generate_waveform(c)

        # Plot it
        p.plot()

    def _update_waveform_frequency(self, c, w):
        """
        Returns the frequency for the settings under the specified root (e.g. c='Ch1', w='Sine')
        """
        s = self.settings
        s.set_value(c+'/'+w, self.get_rate(c)/s[c+'/Samples']*s[c+'/'+w+'/Cycles'], block_key_signals=True)

    def add_channel(self, channel='Ch1', rates=None):
        """
        Adds everything for the specified channel string to the settings. You
        can also override the default rates specified when this object was created.

        Parameters
        ----------
        channel='Ch1' : str
            String channel name.
        rates=None
            Overrides the default rates specified when this object was created.
        """
        s = self.settings
        c = channel
        self._channels.append(c)
        self.plot_design['t_'+c] = []
        self.plot_design[c]      = []

        # Connect all new settings to this function
        s.default_signal_changed = self._settings_changed

        # Add the channel heading / enabler
        s.add_parameter(c, True, tip='Enable '+c+' output')

        # Figure out the rates
        if rates is None: rates = self._rates

        # If we got a single value, it should be a floating point number
        if not _s.fun.is_iterable(rates):
            s.add_parameter(c+'/Rate', rates, bounds=(1e-9, None), dec=True, siPrefix=True, suffix='Hz', tip='Output sampling rate (synced with Samples and Time).')
        else:
            rate_strings = []
            for a in rates: rate_strings.append(str(a))
            s.add_parameter(c+'/Rate', rate_strings, tip='Output sampling rate (Hz, synced with Samples and Time).')

        s.add_parameter(c+'/Samples',  1000.0, bounds=(1,     None), dec=True, suffix='S', siPrefix=True, tip='Number of samples in the waveform (synced with Time and Rate).')
        s.add_parameter(c+'/Samples/Min', 256, int=True, bounds=(2,None), tip='Minimum number of samples allowed to achieve desired frequencies.')
        s.add_parameter(c+'/Samples/Max',8192, int=True, bounds=(2,None), tip='Maximum number of samples allowed to achieve desired frequencies.')

        s.add_parameter(c+'/Time',     0.0,    bounds=(1e-12, None), dec=True, suffix='s', siPrefix=True, tip='Duration of waveform (synced with Samples and Rate).')
        s.add_parameter(c+'/Waveform', ['Square', 'Sine', 'Pulse_Decay', 'Custom'], tip='Choose a waveform. "Custom" corresponds to whatever data you add to self.plot_design.')

        # Sine
        s.add_parameter(c+'/Sine',           0.0,   suffix='Hz', siPrefix=True, tip='Frequency (from settings below).')
        s.add_parameter(c+'/Sine/Cycles',      8,   dec=True, tip='How many times to repeat the waveform within the specified number of samples.' )
        s.add_parameter(c+'/Sine/Amplitude', 0.1,   step=0.1, suffix='V', siPrefix=True, tip='Amplitude (not peak-to-peak).')
        s.add_parameter(c+'/Sine/Offset',    0.0,   step=0.1, suffix='V', siPrefix=True, tip='Offset.')
        s.add_parameter(c+'/Sine/Phase',     0.0,   step=5, suffix=' deg', tip='Phase of sine (90 corresponds to cosine).')

        # Square
        s.add_parameter(c+'/Square',       0.0, suffix='Hz', siPrefix=True, tip='Frequency (from settings below).')
        s.add_parameter(c+'/Square/Cycles',  8, dec=True, tip='How many times to repeat the waveform within the specified number of samples.' )
        s.add_parameter(c+'/Square/High',  0.1, step=0.1, suffix='V', siPrefix=True, tip='High value.')
        s.add_parameter(c+'/Square/Low',   0.0, step=0.1, suffix='V', siPrefix=True, tip='Low value.')
        s.add_parameter(c+'/Square/Start', 0.0, step=0.01, bounds=(0,1), tip='Fractional position within a cycle where the voltage goes high.')
        s.add_parameter(c+'/Square/Width', 0.5, step=0.01, bounds=(0,1), tip='Fractional width of square pulse within a cycle.')

        # Square
        s.add_parameter(c+'/Pulse_Decay/Amplitude', 0.1, step=0.1, suffix='V',  siPrefix=True, tip='Pulse amplitude.')
        s.add_parameter(c+'/Pulse_Decay/Offset',    0.0, step=0.1, suffix='V',  siPrefix=True, tip='Baseline offset.')
        s.add_parameter(c+'/Pulse_Decay/Tau',       0.1,   suffix='s',  siPrefix=True, dec=True, tip='Exponential decay time constant.')
        s.add_parameter(c+'/Pulse_Decay/Zero',      False, tip='Whether to zero the output voltage at the end of the pulse.')

        # Loop option
        s.add_parameter(c+'/Loop', True, tip='Whether the waveform should loop.')


        self._waveforms = ['Sine', 'Square', 'Pulse_Decay']

        # Update the visble items based on selection
        self._settings_select_waveform(c)

        # Update the waveforms
        self._settings_changed()
        self._sync_rates_samples_time(channel+'/Samples')
        self._sync_channels(channel)

        return self

    def after_settings_changed(*a):
        """
        Dummy function called after the settings change and everything updates.
        This receives the same arguments as the signal handler.
        """
        return

    def get_rate(self, channel='Ch1'):
        """
        Returns the output sampling rate (Hz) for the specified channel.

        This function should be overloaded if you use a list of strings for your rates.
        """
        return float(self.settings[channel+'/Rate'])





if __name__ == '__main__':

    _egg.clear_egg_settings()
    #self = signal_chain()
    self = waveform_designer(sync_samples=True, sync_rates=True)
    self.add_channel('Ch1',7000).add_channel('Ch2',5000)
    self.show()
