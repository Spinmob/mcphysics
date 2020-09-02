import spinmob.egg as _egg
import spinmob     as _s
import numpy       as _n
import os          as _os

# Shortcuts
_g = _egg.gui
_p = _s._p
_x = None



def get_nearest_frequency_settings(f_target=12345.678, rate=10e6, min_samples=200, max_samples=8096, buffer_increment=1):
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

    buffer_increment=1 : int
        Enforce that the output buffer size is an integer multiple of this.
        For the adalm2000, e.g., this must be 4 as of v0.2.1 libm2k

    Returns
    -------
    nearest achievable frequency

    number of full cycles within the buffer for this frequency

    buffer size to achieve this
    """

    # Make sure min_samples and max_samples are integer multiples of buffer_increment
    max_samples = max_samples - max_samples%buffer_increment
    min_samples = min_samples - min_samples%buffer_increment + buffer_increment

    # Number of points needed to make one cycle.
    if f_target: N1 = rate / f_target # This is a float with a remainder
    else:        return 0.0, 1, min_samples

    # The goal now is to add an integer number of these cycles up to the
    # max_samples and look for the one with the smallest remainder.
    max_cycles = int(        max_samples/N1 )
    min_cycles = int(_n.ceil(min_samples/N1))

    # List of precise buffer sizes (floating point) to consider.
    # We want to pick the one that is the closest to an integer multiple
    # of buffer_increment.
    options = _n.array(range(min_cycles,max_cycles+1)) * N1

    # How close each option is to an allowed number of samples
    mods = options % buffer_increment
    residuals = _n.minimum(mods, abs(mods-buffer_increment))

    # Find the best fit.
    if len(residuals):

        # Now we can get the exact number of cycles for the smallest residuals
        Nxact = options[_n.argmin(residuals)]

        # Round Nxact to the nearest allowed buffer size.
        residual = Nxact % buffer_increment
        if residual < 0.5*buffer_increment: N = Nxact - residual
        else:                               N = Nxact - residual + buffer_increment

        # If this is below the minimum value, set it to the minimum
        # Not sure how this could happen.
        if N < min_samples: N = min_samples

    # Single period does not fit. Use the maximum number of samples to get the lowest possible frequency.
    else: N = max_samples

    # Now, given this number of points, which might include several oscillations,
    # calculate the actual closest frequency
    df = rate/N                     # Allowed frequencies for this N
    n  = int(_n.round(f_target/df)) # Number of cycles
    f  = n*df                       # Actual frequency that fits.
    return f, n, N

class data_processor(_g.Window):
    """
    Tab area containing a raw data tab and signal processing tabs.

    Parameters
    ----------
    name='data_processor'
        Unique identifier for autosettings. Make sure it is unique!
    margins=False
        Whether to include margins around this.

    **kwargs are sent to the raw databox plot.
    """
    def __init__(self, name='data_processor', margins=False, **kwargs):

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

    rates=1000
        Can be a list of available output rates (Hz, numbers or strings), or number (Hz).
        You are responsible for overloading self.get_rate if you use a list of strings!

    name='waveform_designer'
        Unique identifier for autosettings. Make sure it is unique!

    sync_rates=False
        Set to True to automatically synchronize the rates between channels.

    sync_samples=False
        Set to True to automatically synchronize the number of output samples between channels.

    buffer_increment=1 : int
        Force the output buffer to be an integer multiple of this value. For
        the ADALM2000 and libm2k v0.2.1, this is 4.

    get_rate=None
        Optional function to overload the default self.get_rate()

    margins=False
        Whether to include margins around this.

    **kwargs are sent to the waveform DataboxPlot.
    """
    def __init__(self, rates=1000, name='waveform_designer',
                 sync_rates=False, sync_samples=False,
                 buffer_increment=1,
                 get_rate=None, margins=False, **kwargs):
        _g.Window.__init__(self, title=name, margins=margins, autosettings_path=name)

        # Overload
        if get_rate: self.get_rate = get_rate
        self.buffer_increment=buffer_increment

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
            max_samples = self.settings[channel+'/Samples/Max'],
            buffer_increment = self.buffer_increment)

        # Now update the settings
        self.settings.set_value(channel+'/Samples', samples, block_key_signals=True)
        self.settings.set_value(key    +'/Cycles' , cycles,  block_key_signals=True)

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
            # Update the other quantities in the settings
            self.update_other_quantities_based_on(self.settings.get_key(a[0]))

        # Update the channels in settings
        for c in self._channels: 
            
            # Select the appropriate waveform / hide the others
            self._settings_select_waveform(c)
            

        # Update the other parameters and generate waveforms
        self.update_design()

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
            
            # Catch an infinite loop
            if s[x[0]+'/Samples/Max'] <= s[x[0]+'/Samples/Min']:  s.set_value(x[0]+'/Samples/Max', 2*s[x[0]+'/Samples/Min'], block_key_signals=True)
            
            # If samples is out of range, do the whole process again.
            if x[1] in ['Samples']:
                if   s[x[0]+'/Samples'] > s[x[0]+'/Samples/Max']: s[x[0]+'/Samples'] = s[x[0]+'/Samples/Max']
                elif s[x[0]+'/Samples'] < s[x[0]+'/Samples/Min']: s[x[0]+'/Samples'] = s[x[0]+'/Samples/Min']

            # If Rate or Time changed, set the number of samples, rounding
            if x[1] in ['Rate', 'Time']: s.set_value(x[0]+'/Samples', _n.ceil(s[x[0]+'/Time'] * self.get_rate(x[0])), block_key_signals=False)

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


    def update_design(self):
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

    def add_channels(self, *args, rates=None):
        """
        Adds multiple channels, one for each argument (str). See add_channel()
        for more information.
        """
        for a in args: self.add_channel(a, rates=rates)
        return self

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
            s.add_parameter(c+'/Rate', float(rates), bounds=(1e-9, None), dec=True, siPrefix=True, suffix='Hz', tip='Output sampling rate (synced with Samples and Time).')
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

    def update_other_quantities_based_on(self, key):
        """
        Given the "master" key, (e.g. 'Rate'), calculate and update all other
        dependent quantities, and sync channels if we're supposed to.
        """

        # Update the other quantities for this channel
        self._sync_rates_samples_time(key)

        name   = key.split('/')[-1]
        parent = key.split('/')[-2]

        if name == 'Samples':
            s = self.settings
            v = s[key]

            # Enforce the buffer increment
            r = s[key] % self.buffer_increment
            if r: v = s[key] - r + self.buffer_increment

            # Enforce the min max
            if v > s[key+'/Max']: v = s[key+'/Max']
            if v < s[key+'/Min']: v = s[key+'/Min']

            s.set_value(key, v, block_key_signals=True)


        # If it's a frequency, we have to calculate the closest possible
        if name in ['Sine', 'Square']: self._get_nearest_frequency_settings(key)

        # Sync the other channel settings if we're supposed to.
        if name in ['Rate', 'Samples', 'Time', 'Sine', 'Square']: self._sync_channels(parent)


class quadratures(_g.Window):
    """
    Tabs for calculating quadratures.
    """
    def __init__(self, channels=['Ch1','Ch2'], name='quadratures', margins=False):
        _g.Window.__init__(self, title=name, margins=margins, autosettings_path=name)

        # Internal variables
        self.name = name

        self.grid_left  = self.add(_g.GridLayout(margins=False))
        self.grid_right = self.add(_g.GridLayout(margins=False), alignment=0)

        # # GRID LEFT
        self.grid_left_top  = self.grid_left.add(_g.GridLayout(margins=False), alignment=0)
        self.grid_left.new_autorow()
        self.settings = self.grid_left.add(_g.TreeDictionary(
            autosettings_path  = name+'.settings',
            name               = name+'.settings')).set_width(240)

        # Add the sweep controls
        self.button_sweep = self.grid_left_top.add(_g.Button(
            text            = 'Sweep',
            checkable       = True,
            tip = 'Set outputs, collect data, and estimate quadratures at a variety of frequencies specified below.',
            signal_toggled  = self._button_sweep_toggled_pre), 0,0)

        self.grid_left_top.add(_g.Label('Step:'), 2,0, alignment=2)
        self.number_step = self.grid_left_top.add(_g.NumberBox(
            0, int=True, bounds=(0,None), tip='Current step number.'), 3, 0)
        self.grid_left_top.set_column_stretch(1)

        self.grid_left_top.add(_g.Label('Iteration:'), 2,1, alignment=2)
        self.number_iteration_sweep = self.grid_left_top.add(_g.NumberBox(
            0, int=True, bounds=(0,None), tip='Iteration at this frequency.'), 3,1)

        # Add the sweep settings
        s = self.settings

        for c in channels:
            s.add_parameter('Output/'+c+'_Amplitude', 0.1, step=0.01,
                suffix = '', siPrefix = True,
                tip = 'Amplitude of '+c+' output cosine.')

        s.add_parameter('Input/Settle', 0.1, dec=True,
            suffix = 's', siPrefix = True,
            tip = 'How long to settle after changing the frequency.')

        s.add_parameter('Input/Collect', 0.1, dec=True,
            suffix = 's', siPrefix = True,
            tip = 'Minimum amount of data to collect (will be an integer number of periods).')

        s.add_parameter('Input/Max_Samples', 100000.0, dec=True,
            suffix='S', siPrefix=True, bounds=(100,None),
            tip = 'Maximum allowed input samples (to avoid very long runs, e.g.).')

        s.add_parameter('Input/Iterations', 1.0, dec=True,
            suffix='reps', bounds=(1,None), siPrefix=True,
            tip = 'How many times to repeat the quadrature measurement at each step after settling.')

        s.add_parameter('Sweep/Clear', False,
            tip = 'Clear the Quadratures plot before starting.')

        s.add_parameter('Sweep/Start', 100.0, dec=True,
            suffix = 'Hz', siPrefix=True,
            tip = 'Sweep start frequency.')

        s.add_parameter('Sweep/Stop', 1000.0, dec=True,
            suffix = 'Hz', siPrefix=True,
            tip = 'Sweep stop frequency.')

        s.add_parameter('Sweep/Steps', 10.0, dec=True,
            tip = 'Number of steps from start to stop.')

        s.add_parameter('Sweep/Log_Steps', False,
            tip = 'Whether to use log-spaced steps between Start and Stop.')



        # GRID RIGHT

        self.grid_right_top  = self.grid_right.add(_g.GridLayout(margins=False))
        
        self.grid_right_top.add(_g.Label('Frequency:'))
        self.number_frequency = self.grid_right_top.add(_g.NumberBox(
            1000, step=0.1, dec = True,
            suffix='Hz', siPrefix = True,
            autosettings_path = name+'.number_frequency',
            tip = 'Frequency at which to calculate the quadratures.\nNote this frequency is not guaranteed to "fit" within the\nincoming data, and may not be part of its orthonormal basis.'
            )).set_width(120)

        self.button_get_raw = self.grid_right_top.add(_g.Button(
            text = 'Get Raw',
            signal_clicked = self._button_get_raw_clicked,
            tip  = 'Import the data using self.get_raw(). This is a dummy function you must overload.'))

        self.button_get_quadratures = self.grid_right_top.add(_g.Button(
            text           = 'Get Quadratures',
            signal_clicked = self._button_get_quadratures_clicked,
            tip='Get the quadratures from the data source.').set_width(120))

        self.checkbox_auto = self.grid_right_top.add(_g.CheckBox(
            text              = 'Auto  ',
            autosettings_path = name+'.checkbox_auto',
            tip='Automatically get quadratures for all incoming data.'))

        self.checkbox_truncate = self.grid_right_top.add(_g.CheckBox(
            text              = 'Truncate  ',
            checked           = True,
            autosettings_path = name+'.checkbox_truncate',
            tip='Automatically truncate the data to an integer number of oscillations.'))

        self.button_loop = self.grid_right_top.add(_g.Button(
            text           = 'Loop',
            signal_toggled = self._button_loop_toggled,
            checkable      = True,
            tip='Repeatedly clicks "Get Raw" and "Get Quadratures".'))

        self.number_iteration_total = self.grid_right_top.add(_g.NumberBox(
            0, int=True, tip='Loop iteration (zero\'th column in Quadratures plot.'))



        # # Tabs for plot
        self.grid_right.new_autorow()
        self.tabs = self.grid_right.add(_g.TabArea(autosettings_path=name+'.tabs'), alignment=0)

        self.tab_raw   = self.tabs.add_tab('Quadratures Raw Data')
        self.tab_quad  = self.tabs.add_tab('Quadratures')

        self.plot_raw = self.tab_raw.add(_g.DataboxPlot(
            file_type         = '*.raw',
            autosettings_path = name+'.plot_raw',
            name              = name+'.plot_raw',
            autoscript        = 2), alignment=0)

        self.tab_quad.add(_g.Label('History: '))
        self.number_history = self.tab_quad.add(_g.NumberBox(
            value  = 0,
            step   = 10,
            int    = True,
            bounds = (0, None),
            autosettings_path = name+'.number_history'))

        # self.combo_autoscript = self.tab_quad.add(_g.ComboBox(
        #     ['Autoscript Disabled', 'Magnitude-Phase'],
        #     autosettings_path = name+'.combo_autoscript',
        #     signal_changed = self._combo_autoscript_changed))

        self.tab_quad.new_autorow()

        self.plot_quadratures = self.tab_quad.add(_g.DataboxPlot(
            file_type         = '*.quad',
            autosettings_path = name+'.plot_quadratures',
            name              = name+'.plot_quadratures',
            autoscript        = 1), alignment=0, column_span=3)
        self.tab_quad.set_column_stretch(2)


    def _button_get_quadratures_clicked(self, *a):
        """
        Called when someone clicks the Run button.
        """
        self.get_quadratures()


    def _button_get_raw_clicked(self, *a):
        """
        Called when someone clicks "Get Raw".
        """
        d = self.get_raw()
        if d:
            self.plot_raw.clear()
            self.plot_raw.copy_all(d)
            self.truncate_raw_data()
            self.plot_raw.plot()
            

    def _button_loop_toggled(self, *a):
        """
        When someone toggles the Loop button.
        """
        self.button_loop.set_colors(None, 'Red')
        while self.button_loop():
            self.button_get_raw.click()
            self.button_get_quadratures.click()
            self.process_events()
        self.button_loop.set_colors(None, None)

    def _button_sweep_toggled_pre(self, *a):
        """
        When someone toggles the sweep, clear.
        """
        if self.button_sweep() and self.settings['Sweep/Clear']:
            self.plot_quadratures.clear()

    def get_raw(self):
        """
        Dummy function you must overload. It needs to return a databox or
        DataboxPlot object having time-signal column pairs, e.g., t1, V1, t2, V2, ...
        """
        print('WARNING: quadratures.get_raw() is currently a dummy function that produces simulated data.')
        self.button_get_raw.set_colors('white', 'red')
        
        N = _n.random.randint(700,1000)
        
        d = _s.data.databox()
        t = _n.linspace(0, (N-1)*1e-5, N)
        f = self.number_frequency()
        d['t1'] = t
        d['V1'] = _n.random.normal(size=N)+4*_n.sin(2*_n.pi*f*t)
        d['t2'] = t
        d['V2'] = _n.random.normal(size=N)+4*_n.cos(2*_n.pi*f*t)
        
        return d

    def get_quadratures(self, f=None):
        """
        Calculates the quadratures from the raw data at frequency f.

        Parameters
        ----------
        f=None : float
            Frequency at which to perform the quadrature calculation. If f=None, this will
            use the current value in self.number_frequency.

        Returns
        -------
        The row of data added to self.plot_quadratures
        """
        # Get or set the quadrature frequency.
        if f==None: f = self.number_frequency()
        else:           self.number_frequency(f)

        # Increment
        self.number_iteration_total.increment()

        # Get the source databox and quadrature plotter
        d = self.plot_raw
        p = self.plot_quadratures
        p.copy_headers(d)

        # Assumed column pairs
        row  = [self.number_iteration_total(), f]
        keys = ['n', 'f(Hz)']
        for n in range(0, len(d), 2):

            # Get the time axis and the two quadratures
            t = d[n]
            X = _n.cos(2*_n.pi*f*t)
            Y = _n.sin(2*_n.pi*f*t)

            # Normalize
            X = _n.nan_to_num(X/sum(X*X))
            Y = _n.nan_to_num(Y/sum(Y*Y))

            # Get quadratures
            VX = sum(d[n+1]*X)
            VY = sum(d[n+1]*Y)

            # Append to the row
            row  = row  + [VX, VY]
            keys = keys + [d.ckeys[n+1]+'_X', d.ckeys[n+1]+'_Y']

        # Append the row
        p.append_row(row, keys, self.number_history())

        # Plot!
        p.plot()

    def get_sweep_step_frequency(self, step):
        """
        Returns the frequency at the specified step. Note this step is indexed
        relative to 1 (matching the GUI), so it goes from 1 to
        self.settings['Sweep/Steps'].

        Returns None otherwise.
        """
        step = int(step)
        sd = self.settings
        if step < 1 or step > sd['Sweep/Steps']: return None

        # Get the frequency list.
        if sd['Sweep/Log_Steps']:
            if sd['Sweep/Start'] == 0: sd['Sweep/Start'] = sd['Stop' ]*0.01
            if sd['Sweep/Stop' ] == 0: sd['Sweep/Stop' ] = sd['Start']*0.01
            if sd['Sweep/Start'] == 0: return
            fs = _s.fun.erange(sd['Sweep/Start'], sd['Sweep/Stop'], int(sd['Sweep/Steps']))
        else:
            fs = _n.linspace  (sd['Sweep/Start'], sd['Sweep/Stop'], int(sd['Sweep/Steps']))

        return fs[step-1]

    def truncate_raw_data(self, override_checkbox=False):
        """
        Truncates the raw data to an integer number of periods for the shown
        frequency. Assumes the data in the Raw tab is in time-signal column.
        
        By default, this function will only truncate if the Truncate checkbox
        is enabled. Setting override_checkbox=True will truncate even if it's not.
        """
        if not override_checkbox and not self.checkbox_truncate(): return self
        
        # Shortcuts
        d = self.plot_raw
        f = self.number_frequency()

        # Don't truncate if the frequency is zero.
        if f==0: return self
        
        # Loop over the data.
        for n in range(0, len(d), 2):
            
            # Get the time step and total time
            dt = d[n][1] -d[n][0]
            T  = d[n][-1]-d[n][0]
            
            # Get the number of periods that fits
            N = int(_n.floor(f*T))
            
            # If it's zero, we're hosed
            if N < 1: 
                print('WARNING, quadratures.truncate_raw_data(): Not even one period at frequency',f,'fits within the supplied data; truncation aborted.')
                return self
        
            # Get the truncated time and samples
            T = N/f
            samples = int(_n.round(T/dt))
            
            # Truncate.
            d[n]   = d[n  ][0:samples]
            d[n+1] = d[n+1][0:samples]
         
        return self
            


if __name__ == '__main__':

    _egg.clear_egg_settings()
    # self = data_processor()

    self = waveform_designer(sync_samples=True, sync_rates=True,
                             buffer_increment=4).add_channels('a', 'b')

    #self = quadratures()
    self.show()

    # # Set up the output channels
    # so = self.settings
    # p  = self.plot_design
    # d = dict()
    # c = 'a'
    # so[c+'/Waveform'] = 'Sine'
    # d[c+'/Sine/Offset']    = 0
    # d[c+'/Sine/Phase']     = 90

    # so.update(d, block_key_signals=True)
    # so.set_value(c+'/Rate', 750000.0, block_key_signals=True)
    # so.set_value(c+'/Sine', 2000.0, block_key_signals=True)

    # # Update the actual frequency etc
    # self.update_other_quantities_based_on(c+'/Sine')

    # self.update_design()

    # print(so[c+'/Sine'])

