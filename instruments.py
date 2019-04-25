# Windows:
#  Install Rhode & Schwarz VISA or NI-VISA
#  pip install pyvisa
#  Name the scope something reasonable in OpenChoice Instrument Manager
# 
# Linux
#  pip install pyvisa pyvisa-py
#  Let me know if you find out how to name the scope.

# Feature to implement
#  * Find trigger time and define this to be zero.
#  * Option to query full data set

import numpy   as _n
import time    as _t
import spinmob as _s
import spinmob.egg as _egg
import time    as _time
_g = _egg.gui

try:    import visa as _v
except: print('Visa driver and / or pyvisa not installed. On Windows, consider Rhode & Schwartz VISA or NI-VISA, then pip install pyvisa. On Linux, pip install pyvisa and pyvisa-py')

_debug_enabled = False
def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))







class sillyscope_api():
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
    """
    
    
    def __init__(self, name='TDS1012B', pyvisa_py=False, simulation=False):
        
        # Create a resource management object
        if pyvisa_py: self.resource_manager = _v.ResourceManager('@py')
        else:         self.resource_manager = _v.ResourceManager()
        
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
        
        # If we're in simulation mode, return
        if simulation:
            self.instrument = None
            self._idn = 'Simulation Mode'
            return
        
        # Try to open the instrument.
        try:
            self.instrument = self.resource_manager.open_resource(name)

            # Test that it's responding and is a Tektronix device.
            try:
                # Get the ID of the instrument
                self._idn = idn = self.query('*IDN?').strip()
                
                # Remember if it's a Tektronix scope
                if   idn[0:9] == 'TEKTRONIX': self.model='TEKTRONIX'
                
                # Need to distinguish 'Rigol Technologies,DS1052E,DS1ET161453620,00.04.01.00.02'
                # Which is janky and not working. (What is the GD data format??)
                elif idn[0:5].upper() == 'RIGOL': 
                    
                    # Get the model string
                    m = idn.split(',')[1]
                    
                    # Find out if it's a d/e or a z:
                    if   m[-1] in ['Z']: self.model='RIGOLZ'
                    elif m[-1] in ['B']: self.model='RIGOLB'
                    else:                self.model='RIGOLDE'
                
                # Poop out.
                else: self.model=None
                
                # Set the type of encoding for the binary data returned
                self.set_binary_encoding()
            
            except:
                print("ERROR: Instrument did not reply to IDN query. Entering simulation mode.")
                self.instrument.close()
                self.instrument = None
        except:
            print("ERROR: Could not open instrument. Entering simulation mode.")
            self.instrument = None
            
            # Now list all available resources
            print("Available Instruments:")
            for name in self.resource_manager.list_resources(): print("  "+name)
        
        
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
            d = _s.fun.generate_fake_data('20*sin(x)', _n.linspace(-5,5,1024), 
                                          ey=2, include_errors=False)
            
            # Fake the acquisition time
            _t.sleep(0.01)
            
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
            
            # Transfer the waveform information
            v = self._query_and_decode_waveform()
            
            _debug('_query_and_decode_waveform() done', len(v))
            
            # For duty cycle calculation
            t2 = _t.time()            

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
        if t3-t0>0: self.t_duty_cycle = (t2-t1)/(t3-t0)
        else:       print("WARNING: get_waveform() total time == 0")
        
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
            
            d.insert_header('xzero'+c,       0)#-float(self.query(':WAV:XOR? CHAN'+c)))
            d.insert_header('xmultiplier'+c, xinc)
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
            print('ERROR: get_header() unhandled model '+self.model)
        
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
        
            # Convert it to integers, based on empirically measuring.
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
            _debug('  ERROR: unhandled model '+self.model)

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
            _debug('  ERROR: unhandled model '+self.model)
        
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


            


class sillyscope(_g.BaseObject):
    """
    Graphical front-end for RIGOL 1000 B/D/E/Z and Tektronix TBS/TDS 1000.
    
    Parameters
    ----------
    autosettings_path='sillyscope'
        Which file to use for saving the gui stuff. This will also be the first
        part of the filename for the other settings files.
    
    pyvisa_py=False
        Whether to use pyvisa_py or not.
        
    block=False
        Whether to block the command line while showing the window.
    """
    def __init__(self, autosettings_path='sillyscope', pyvisa_py=False, block=False):
        
        # No scope selected yet
        self.api = None

        # Build the GUI
        self.window    = _g.Window('Sillyscope', autosettings_path=autosettings_path+'window')
        self.window.event_close = self.event_close
        self.grid_top  = self.window.place_object(_g.GridLayout(False))
        self.window.new_autorow()
        self.grid_bot  = self.window.place_object(_g.GridLayout(False), alignment=0)
        
        self.button_connect   = self.grid_top.place_object(_g.Button('Connect', True, False))
        self.button_1         = self.grid_top.place_object(_g.Button('1',True).set_width(25).set_checked(True))
        self.button_2         = self.grid_top.place_object(_g.Button('2',True).set_width(25))
        self.button_3         = self.grid_top.place_object(_g.Button('3',True).set_width(25))
        self.button_4         = self.grid_top.place_object(_g.Button('4',True).set_width(25))
        self.button_acquire   = self.grid_top.place_object(_g.Button('Acquire',True).disable())
        self.number_count     = self.grid_top.place_object(_g.NumberBox(0).disable())
        self.button_waiting   = self.grid_top.place_object(_g.Button('Waiting', True).set_width(70))
        self.button_transfer  = self.grid_top.place_object(_g.Button('Transfer',True).set_width(70))
        self.label_scope_name = self.grid_top.place_object(_g.Label('Disconnected'))
        
        self.settings  = self.grid_bot.place_object(_g.TreeDictionary(autosettings_path+'_settings.txt')).set_width(250)
        self.tabs_data = self.grid_bot.place_object(_g.TabArea(autosettings_path+'_tabs_data.txt'), alignment=0)
        self.tab_raw   = self.tabs_data.add_tab('Raw Data')
        self.plot_raw  = self.tab_raw.place_object(_g.DataboxPlot('*.txt', autosettings_path+'_plot_raw.txt'), alignment=0)
        
        # Keep track of previous plot
        self._previous_data = _s.data.databox()
        
        # Create a resource management object
        if pyvisa_py: self.resource_manager = _v.ResourceManager('@py')
        else:         self.resource_manager = _v.ResourceManager()
        
        names = []
        for x in self.resource_manager.list_resources():
            names.append(x)
                
        # VISA settings
        self.settings.add_parameter('VISA/Device', 0, type='list', values=['Simulation']+names)

        # Acquisition settings
        self.settings.add_parameter('Acquisition/Iterations',       0,    tip='How many iterations to perform. Set to 0 to keep looping.')
        self.settings.add_parameter('Acquisition/Trigger',          True, tip='Halt acquisition and arm / wait for a single trigger.')
        self.settings.add_parameter('Acquisition/Get_First_Header', True, tip='Get the header (calibration) information the first time. Disabling this will return uncalibrated data.')
        self.settings.add_parameter('Acquisition/Get_All_Headers',  True, tip='Get the header (calibration) information EVERY time. Disabling this will use the first header repeatedly.')
        self.settings.add_parameter('Acquisition/Discard_Identical',False,tip='Do not continue until the data is different.')
        
        # Device-specific settings
        self.settings.add_parameter('Acquisition/RIGOL1000BDE/Trigger_Delay', 0.05, bounds=(1e-3,10), siPrefix=True, suffix='s', dec=True, tip='How long after "trigger" command to wait before checking status. Some scopes appear to be done for a moment between the trigger command and arming.')
        self.settings.add_parameter('Acquisition/RIGOL1000BDE/Unlock',        True, tip='Unlock the device\'s frong panel after acquisition.')
        self.settings.add_parameter('Acquisition/RIGOL1000Z/Always_Clear',    True, tip='Clear the scope prior to acquisition even in untriggered mode (prevents duplicates but may slow acquisition).')
        
        # Connect all the signals
        self.settings.connect_signal_changed('Acquisition/Trigger', self._settings_trigger_changed)
        self.button_connect.signal_clicked.connect(self.button_connect_clicked)
        self.button_acquire.signal_clicked.connect(self.button_acquire_clicked)
        self.button_1.signal_toggled.connect(self.save_gui_settings)
        self.button_2.signal_toggled.connect(self.save_gui_settings)
        self.button_3.signal_toggled.connect(self.save_gui_settings)
        self.button_4.signal_toggled.connect(self.save_gui_settings)
        


        # Convenience
        self.d = self.plot_raw

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=autosettings_path)
        self._autosettings_controls = ['self.button_1', 'self.button_2',
                                       'self.button_3', 'self.button_4']
        self.load_gui_settings()
        
        
        # Show the window.
        self.window.show(block)
    
    def _unlock(self):
        """
        If we're using a RIGOLDE/B and wish to unlock, send the :FORC command.
        """
        if self.settings['Acquisition/RIGOL1000BDE/Unlock']:
            if self.api.model in ['RIGOLDE']:
                self.api.write(':KEY:FORC')   
            elif self.api.model in ['RIGOLB']:
                self.api.write(':KEY:LOCK DIS')
    
    def _settings_trigger_changed(self, *a):
        """
        Called when someone clicks the Trigger checkbox.
        """
        if self.settings['Acquisition/Trigger']: 
            self.api.set_mode_single_trigger()
            self._unlock()
    
    def connect(self):
        """
        Pushes the Connect button.
        """
        self.button_connect.set_checked()
        self.button_connect_clicked()

    def acquire(self):
        """
        Presses the Acquire button.
        """
        self.button_acquire.set_checked()
        self.button_acquire_clicked()        

    def get_status_finished(self):
        """
        Returns True if the acquisition is complete.
        
        For RIGOL scopes, this uses get_waveforms(), which also updates 
        self.plot_raw(), which is the best way to get the status. This avoids
        the issue of the single trigger taking time to get moving.
        """
        _debug('get_status_finished()')
        
        if self.api.model == 'TEKTRONIX':
            _debug('  TEK')
            return not bool(int(self.api.query('ACQ:STATE?')))
        
        elif self.api.model == 'RIGOLZ':
            _debug('  RIGOLZ')
            
            # If the waveforms are empty (we cleared it!)
            self.get_waveforms()
            if len(self.plot_raw[0]) > 0: return True
            else:                         return False
       
        elif self.api.model in ['RIGOLDE', 'RIGOLB']:
            _debug('  RIGOLDE/B')
                        
            self.window.sleep(self.settings['Acquisition/RIGOL1000BDE/Trigger_Delay'])
            s = self.api.query(':TRIG:STAT?').strip()
            return s == 'STOP'
            

    def get_waveforms(self):
        """
        Queries all the waveforms that are enabled, overwriting self.plot_raw
        """
        _debug('get_waveforms()')
        
        
        # Find out if we should get the header
        get_header = self.settings['Acquisition/Get_All_Headers']  \
                  or self.settings['Acquisition/Get_First_Header'] \
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
            
            # Update teh main plot
            self.plot_raw['x']  = d['x']
            self.plot_raw['y2'] = d['y2']
            self.plot_raw.copy_headers(d)
            self.window.process_events()
        
        # If we're supposed to get curve 2
        if self.button_3.get_value():
            
            # Actually get it
            d = self.api.get_waveform(3, use_previous_header=not get_header)
            
            # Update teh main plot
            self.plot_raw['x']  = d['x']
            self.plot_raw['y3'] = d['y3']
            self.plot_raw.copy_headers(d)
            self.window.process_events()
          
        # If we're supposed to get curve 2
        if self.button_4.get_value():
            
            # Actually get it
            d = self.api.get_waveform(4, use_previous_header=not get_header)
            
            # Update teh main plot
            self.plot_raw['x']  = d['x']
            self.plot_raw['y4'] = d['y4']
            self.plot_raw.copy_headers(d)
            self.window.process_events()
        
        # Tell the user we're done transferring data
        self.button_transfer.set_checked(False)
        self.window.process_events()
        
        _debug('get_waveforms() complete')

        

    def button_connect_clicked(self, *a):
        """
        Connects or disconnects the VISA resource.
        """
        
        # If we're supposed to connect
        if self.button_connect.get_value():
            
            # Close it if it exists for some reason
            if not self.api == None: self.api.instrument.close()
            
            # Make the new one
            self.api = sillyscope_api(self.settings['VISA/Device'], 
                simulation = self.settings['VISA/Device']=='Simulation')
            
            # Tell the user what scope is connected
            self.label_scope_name.set_text(self.api._idn)
            
            # Enable the Acquire button
            self.button_acquire.enable()
            
        elif not self.api == None:
            
            # Close down the instrument
            if not self.api.instrument == None:
                self.api.instrument.close()
            self.api = None
            self.label_scope_name.set_text('Disconnected')
            
            # Disable the acquire button
            self.button_acquire.disable()
            
    def button_acquire_clicked(self, *a):
        """
        Get the enabled curves, storing them in plot_raw.
        """
        _debug('button_acquire_clicked()')
        
        # Don't double-loop!
        if not self.button_acquire.is_checked(): return

        # Don't proceed if we have no connection
        if self.api == None: 
            self.button_acquire.set_checked(False)
            return

        # Disable the connection button
        self.button_connect.disable()
        
        # Reset the counter
        self.number_count.set_value(0)
        
        # If we're triggering, set to single sequence mode
        if self.settings['Acquisition/Trigger']: 
            self.api.set_mode_single_trigger()
            
        _debug('  beginning loop')

        # Continue until unchecked        
        while self.button_acquire.is_checked():
            
            # Update the user
            self.button_waiting.set_checked(True)
            
            # Transfer the current data to the previous
            self._previous_data.clear()
            self._previous_data.copy_all(self.plot_raw)
            
            # Trigger
            if self.settings['Acquisition/Trigger']:
                
                _debug('  TRIGGERING')
                
                # Set it to acquire the sequence.
                self.api.trigger_single() # For RigolZ, this clears the trace
                
                # Simulation mode: "wait" for it to finish
                _debug('  WAITING')
                if self.api.instrument == None: self.window.sleep(0.1)
                
                # Actual scope: wait for it to finish
                else:
                    while not self.get_status_finished() and self.button_acquire.is_checked(): 
                        self.window.sleep(0.02)
                
                # Tell the user it's done acquiring.
                _debug('  TRIGGERING DONE')
            
            # For RIGOL scopes, the most reliable / fast way to wait for a trace
            # is to clear it and keep asking for the waveform.
            
            # Not triggering but RIGOLZ mode: clear the data first and then wait for data
            elif self.api.model in ['RIGOLZ']:
                
                # Clear the scope if we're not in free running mode
                if self.settings['Acquisition/RIGOL1000Z/Always_Clear']:
                    self.api.write(':CLE')
                    
                # Wait for it to complete
                while not self.get_status_finished() and self.button_acquire.is_checked(): 
                    self.window.sleep(0.005)
            
            
            self.button_waiting.set_checked(False)
                
            # If the user hasn't canceled yet
            if self.button_acquire.is_checked():
                
                _debug('  getting data')
        
                # The Z RIGOL models best check the status by getting the waveforms
                # after clearing the scope and seeing if there is data returned.
                
                # Triggered RIGOLZ scopes already have the data
                if self.api.model in [None, 'TEKTRONIX', 'RIGOLDE', 'RIGOLB'] or \
                   not self.settings['Acquisition/Trigger']: 
                       
                       # Query the scope for the data and stuff it into the plotter
                       self.get_waveforms()
                       _debug('  got '+str(self.plot_raw))
                
                _debug('  processing')
            
                # Increment the counter, but only if the data is new
                self.number_count.increment()
                
                # Decrement if it's identical to the previous trace
                if self.settings['Acquisition/Discard_Identical']:
                    is_identical = self.plot_raw == self._previous_data
                    _debug('  Is identical to previous?', is_identical)
                    if is_identical: self.number_count.increment(-1)
                
                # Update the plot
                _debug('  plotting', len(self.plot_raw[0]), len(self.plot_raw[1]))
                self.plot_raw.plot()
                
                _debug('  plotting done')
                self.window.process_events()
        
                # Autosave if enabled.
                _debug('  autosaving')
                self.plot_raw.autosave()
            
                # End condition
                _debug('  checking end condition')
                N = self.settings['Acquisition/Iterations']
                if self.number_count.get_value() >= N and not N <= 0: 
                    self.button_acquire.set_checked(False)
        
        _debug('  loop done')
        
        # Enable the connect button
        self.button_connect.enable()
        
        # Unlock the RIGOL1000E front panel
        self._unlock()
    
    
    
    def event_close(self, *a):
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
    """
    
    
    
    def __init__(self, name='ASRL3::INSTR', pyvisa_py=False):
        
        # Create a resource management object
        if pyvisa_py: self.resource_manager = _v.ResourceManager('@py')
        else:         self.resource_manager = _v.ResourceManager()
        
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
            print("ERROR: Could not open instrument. Entering simulation mode.")
            self.instrument = None
            
            # Now list all available resources
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
        
        self.button_acquire   = self.grid_top.place_object(_g.Button('Acquire',True).disable())
        self.label_dmm_name   = self.grid_top.place_object(_g.Label('Disconnected'))
        
        self.settings  = self.grid_bot.place_object(_g.TreeDictionary(autosettings_path+'_settings.txt')).set_width(250)
        self.tabs_data = self.grid_bot.place_object(_g.TabArea(autosettings_path+'_tabs_data.txt'), alignment=0)
        self.tab_raw   = self.tabs_data.add_tab('Raw Data')
        self.plot_raw  = self.tab_raw.place_object(_g.DataboxPlot('*.txt', autosettings_path+'_plot_raw.txt', autoscript=2), alignment=0)
        
        # Create a resource management object to populate the list
        if pyvisa_py: self.resource_manager = _v.ResourceManager('@py')
        else:         self.resource_manager = _v.ResourceManager()
        names = []
        for x in self.resource_manager.list_resources(): names.append(x)
                
        # VISA settings
        self.settings.add_parameter('VISA/Device', 0, type='list', values=['Simulation']+names)

        # Acquisition settings
        self.settings.add_parameter('Acquisition/Unlock', True, tip='Unlock the device\'s front panel after acquisition.')
        
        # Connect all the signals
        self.button_connect.signal_clicked.connect(self.button_connect_clicked)
        self.button_acquire.signal_clicked.connect(self.button_acquire_clicked)
        
        # Convenience
        self.d = self.plot_raw

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=autosettings_path)
        self._autosettings_controls = [
                                       'self.buttons[0]', 'self.buttons[1]',
                                       'self.buttons[2]', 'self.buttons[3]',
                                       'self.buttons[4]', 'self.buttons[5]',
                                       'self.buttons[6]', 'self.buttons[7]']
        self.load_gui_settings()
        
        # Show the window.
        self.window.show(block)

    def button_connect_clicked(self, *a):
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
            if self.api.instrument == None: self.label_dmm_name.set_text('Simulation')
            else:                           self.label_dmm_name.set_text(self.api.model)
            
            # Enable the Acquire button
            self.button_acquire.enable()
            
        elif not self.api == None:
            
            # Close down the instrument
            if not self.api.instrument == None:
                self.api.close()
            self.api = None
            self.label_dmm_name.set_text('Disconnected')
            
            # Disable the acquire button
            self.button_acquire.disable()
            
    def button_acquire_clicked(self, *a):
        """
        Get the enabled curves, storing them in plot_raw.
        """
        _debug('button_acquire_clicked()')
        
        # Don't double-loop!
        if not self.button_acquire.is_checked(): return

        # Don't proceed if we have no connection
        if self.api == None: 
            self.button_acquire.set_checked(False)
            return

        # Ask the user for the dump file
        self.path = _s.dialogs.save('*.csv', 'Select an output file.', force_extension='*.csv')
        if self.path == None: return
    
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
        if self.settings['Acquisition/Unlock']: self.api.unlock()
        
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
         
    self = keithley_dmm_api()
    