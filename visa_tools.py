import time    as _t
import spinmob.egg as _egg
_g = _egg.gui

import traceback as _traceback
_p = _traceback.print_last

try:    import visa as _v
except: print('Visa driver and / or pyvisa not installed. On Windows, consider Rhode & Schwartz VISA or NI-VISA, then pip install pyvisa. On Linux, pip install pyvisa and pyvisa-py')

_debug_enabled = False
def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))





class visa_api_base():
    """
    Handles the visa infrastructure common to all instrument drivers.
    
    Parameters
    ----------
    name='VISA_Alias'
        Name of the instrument, as it appears in the VISA resource manager.
    
    pyvisa_py=False
        Set to True if using pyvisa-py instead of, e.g., R&S VISA or NI-VISA.
    
    simulation=False
        Set to True to enable simulation mode.
    
    timeout=2000
        Command timeout in ms.
        
    write_sleep=0
        How many seconds to sleep after each write.
    """
    
    
    def __init__(self, name='VISA_Alias', pyvisa_py=False, simulation=False, timeout=2000, write_sleep=0.01):
        _debug('api_base.__init__()')
        # Store it
        self._write_sleep = write_sleep
        self.idn         = None
        
        # Create a resource management object
        if pyvisa_py: self.resource_manager = _v.ResourceManager('@py')
        else:         self.resource_manager = _v.ResourceManager()
        
        # If we're in simulation mode, return
        if simulation:
            self.instrument = None
            self.idn = 'Simulation Mode'
            return
        
        # Try to open the instrument.
        try:
            self.instrument = self.resource_manager.open_resource(name)
            
            # Test that it's responding and is a Tektronix device.
            try:
                # Set the timeout
                self.instrument.timeout = timeout
                
                # Get the ID of the instrument
                self.idn = self.query('*IDN?').strip()
                
            except:
                print("ERROR: Instrument did not reply to IDN query. Entering simulation mode.")
                self.instrument.close()
                self.instrument = None
                self.idn = "Simulation Mode"
        
        except:
            print("ERROR: Could not open instrument. Entering simulation mode.")
            self.instrument = None
            self.idn = "Simulation Mode"
            
            # Now list all available resources
            print("Available Instruments:")
            for name in self.resource_manager.list_resources(): 
                print("  " + str(self.resource_manager.resource_info(name).alias))
        
        
    # These can be modified later to make them safe, add delays, etc.
    def command(self, message='*IDN?'):
        """
        Shortcut for coding. Runs a query() if there is a question mark, and a write() if there is not.
        """
        _debug('api_base.command('+message+')')
        
        if message.find('?') >= 0: return self.query(message)
        else:                      return self.write(message)
    
    def query(self, message='*IDN?'):
        """
        Sends the supplied message and returns the response.
        """
        _debug('api_base.query('+"'"+message+"'"+')')
        
        if self.instrument == None:
            _t.sleep(self._write_sleep)
            return
        else: 
            self.write(message)
            return self.read()
    
    def write(self, message): 
        """
        Writes the supplied message.
        """
        _debug('api_base.write('+"'"+message+"'"+')')
        
        if self.instrument == None: 
            _t.sleep(self._write_sleep)
            return
        else:
            x = self.instrument.write(message)
            _t.sleep(self._write_sleep)
            return x
        
    
    def read (self):          
        """
        Reads a message and returns it.
        """
        _debug('api_base.read()')
        
        if self.instrument == None: return
        else:                       
            s = self.instrument.read()
            _debug('  '+str(s))
            return s
    
    def read_raw(self):       
        """
        Reads a raw message (e.g. a binary stream) and returns it.
        """
        _debug('api_base.read_raw()')
        
        if self.instrument == None: return 
        else:                       
            s = self.instrument.read_raw()
            _debug('  '+ str(s))
            return s


class visa_gui_base(_g.BaseObject):
    """
    Handles the common features of our visa graphical front-ends
    
    Parameters
    ----------
    name='visa_gui'
        Make this unique for each object in a larger project. This 
        will also be the first part of the filename for the other settings files.
   
    show=True
        Whether to show the window immediately.
         
    block=False
        Whether to block the command line while showing the window.
    
    api=visa_api_base
        Class to use for the api. Should have at least the base functionality of
        visa_api_base, and take the same init arguments.
    
    timeout=2000
        Command timeout (ms)
    
    write_sleep
        How long to sleep after writing a message (sec)
    
    pyvisa_py=False
        Whether to use pyvisa_py or not.
        
    window_size=[1,1]
        Default window size.
   
    """
    def __init__(self, name='visa_gui', show=True, block=False, api=visa_api_base, timeout=2000, write_sleep=0.01, pyvisa_py=False, window_size=[1,1]):
        _debug('gui_base.__init__()')
        
        # Remember the name
        self.name = name
        self._write_sleep = write_sleep
        self._timeout     = timeout
        
        # No instrument selected yet
        self.api = None
        self._api_base = api

        # Build the GUI
        self.window    = _g.Window(name, size=window_size, autosettings_path=name+'_window.txt')
        self.grid_top  = self.window.place_object(_g.GridLayout(False))
        self.window.new_autorow()
        self.grid_bot  = self.window.place_object(_g.GridLayout(False), alignment=0)
        
        self.button_connect        = self.grid_top.place_object(_g.Button('Connect', True, False)).set_width(60)
        self.label_instrument_name = self.grid_top.place_object(_g.Label('Disconnected'), 100, 0)
        
        self.settings  = self.grid_bot.place_object(_g.TreeDictionary(name+'_settings.txt', name), alignment=0)
        
        # Create a resource management object
        self._pyvisa_py = pyvisa_py
        if pyvisa_py: self.resource_manager = _v.ResourceManager('@py')
        else:         self.resource_manager = _v.ResourceManager()
        
        # Get a list of resource names and a dictionary of device aliases
        # To convert from the "easy" name in the combo to the "real" name.
        names = []
        self._device_aliases = dict()
        for x in self.resource_manager.list_resources():
            alias = self.resource_manager.resource_info(x).alias
            if alias == None:
                self._device_aliases[x] = x
                names.append(x)
            else:
                self._device_aliases[alias] = x
                names.append(alias)
                
        # VISA settings
        self.settings.add_parameter('VISA/Device', 0, type='list', values=['Simulation']+names)

        # Connect the signals
        self.button_connect.signal_toggled.connect(self._button_connect_clicked)
        
        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=name)
        
        # Show the window.
        if show: self.window.show(block)

    def _button_connect_clicked(self, *a):
        """
        Connects or disconnects the VISA resource.
        """
        _debug('gui_base._button_connect_clicked', a)
        
        # If we're supposed to connect
        if self.button_connect.get_value():
            
            # Close it if it exists for some reason
            if not self.api == None: self.api.instrument.close()
            
            # Make the new one
            self.api = self._api_base(name       = self.settings['VISA/Device'], 
                                      pyvisa_py  = self._pyvisa_py,
                                      simulation = self.settings['VISA/Device']=='Simulation',
                                      timeout    = self._timeout,
                                      write_sleep= self._write_sleep)
            
            # Tell the user what scope is connected
            self.label_instrument_name.set_text(self.api.idn)
        
            # Connecting was successful!
            self._after_connect()
            
             
            
        # FAIL.
        elif not self.api == None:
            
            # Close down the instrument
            if not self.api.instrument == None: self.api.instrument.close()
            self.api = None
            self.label_instrument_name.set_text('Disconnected')
            self.button_connect.set_checked(False, block_events=True)
            
            # Disconnection successful!
            self._after_disconnect()


    def _after_connect(self):
        """
        Overload this function to define what happens after a successful connection.
        """
        _debug('gui_base._after_connect()')
        return

    def _after_disconnect(self):
        """
        Overload this function to define what happens after a successful disconnection.
        """
        _debug('gui_base._after_disconnect()')
        return

if __name__ == '__main__':
    self = visa_gui_base()