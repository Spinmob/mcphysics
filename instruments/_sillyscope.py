import numpy   as _n
import time    as _t
import spinmob as _s
import spinmob.egg as _egg
_g = _egg.gui
import mcphysics as _mp

try: from . import _visa_tools
except: _visa_tools = _mp.instruments._visa_tools

_mp._debug_enabled = False
_debug = _mp._debug

class sillyscope_api(_visa_tools.visa_api_base):
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
        _visa_tools.visa_api_base.__init__(self, name=name, pyvisa_py=pyvisa_py, simulation=simulation, timeout=timeout, write_sleep=write_sleep)

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





class sillyscope(_visa_tools.visa_gui_base):
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
        _visa_tools.visa_gui_base.__init__(self, name=name, show=False, block=False, api=sillyscope_api, pyvisa_py=pyvisa_py, window_size=[1000,500])

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

if __name__ == '__main__':
    self = sillyscope()