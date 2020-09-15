import spinmob.egg as _egg
import traceback as _traceback
_p = _traceback.print_last
_g = _egg.gui
import spinmob as _s
import time as _time

try: import serial as _serial
except: _serial = None

try: from serial.tools.list_ports import comports as _comports
except: _comports = None

def get_com_ports():
    """
    Returns a dictionary of port names as keys and descriptive names as values.
    """
    if _comports:

        ports = dict()
        for p in _comports(): ports[p.device] = p.description
        return ports

    else:
        raise Exception('You need to install pyserial and have Windows to use get_com_ports().')

def list_com_ports():
    """
    Prints a "nice" list of available COM ports.
    """
    ports = get_com_ports()

    # Empty dictionary is skipped.
    if ports:
        keys = list(ports.keys())
        keys.sort()
        print('Available Ports:')
        for key in keys:
            print(' ', key, ':', ports[key])

    else: raise Exception('No ports available. :(')

class serial_gui_base(_g.BaseObject):
    """
    Base class for creating a serial connection gui. Handles common controls.

    Parameters
    ----------
    api_class=None : class
        Class to use when connecting. For example, api_class=auber_syl53x2p_api would
        work. Note this is not an instance, but the class itself. An instance is
        created when you connect and stored in self.api.

    name='serial_gui' : str
        Unique name to give this instance, so that its settings will not
        collide with other egg objects.

    show=True : bool
        Whether to show the window after creating.

    block=False : bool
        Whether to block the console when showing the window.

    window_size=[1,1] : list
        Dimensions of the window.

    hide_address=False: bool
        Whether to show the address control for things like the Auber.
    """
    def __init__(self, api_class=None, name='serial_gui', show=True, block=False, window_size=[1,1], hide_address=False):

        # Remebmer the name.
        self.name = name

        # Checks periodically for the last exception
        self.timer_exceptions = _g.TimerExceptions()
        self.timer_exceptions.signal_new_exception.connect(self._new_exception)

        # Where the actual api will live after we connect.
        self.api = None
        self._api_class = api_class

        # GUI stuff
        self.window   = _g.Window(
            self.name, size=window_size, autosettings_path=name+'.window',
            event_close = self._window_close)
        self.grid_top = self.window.place_object(_g.GridLayout(margins=False), alignment=0)
        self.window.new_autorow()
        self.grid_bot = self.window.place_object(_g.GridLayout(margins=False), alignment=0)

        # Get all the available ports
        self._label_port = self.grid_top.add(_g.Label('Port:'))
        self._ports = [] # Actual port names for connecting
        ports       = [] # Pretty port names for combo box
        if _comports:
            for p in _comports():
                self._ports.append(p.device)
                ports      .append(p.description)

        ports      .append('Simulation')
        self._ports.append('Simulation')
        self.combo_ports = self.grid_top.add(_g.ComboBox(ports, autosettings_path=name+'.combo_ports'))

        self.grid_top.add(_g.Label('Address:')).show(hide_address)
        self.number_address = self.grid_top.add(_g.NumberBox(
            0, 1, int=True,
            autosettings_path=name+'.number_address',
            tip='Address (not used for every instrument)')).set_width(40).show(hide_address)

        self.grid_top.add(_g.Label('Baud:'))
        self.combo_baudrates = self.grid_top.add(_g.ComboBox(
            ['1200', '2400', '4800', '9600', '19200'],
            default_index=3,
            autosettings_path=name+'.combo_baudrates'))

        self.grid_top.add(_g.Label('Timeout:'))
        self.number_timeout = self.grid_top.add(_g.NumberBox(2000, dec=True, bounds=(1, None), suffix=' ms', tip='How long to wait for an answer before giving up (ms).', autosettings_path=name+'.number_timeout')).set_width(100)

        # Button to connect
        self.button_connect  = self.grid_top.add(_g.Button('Connect', checkable=True))

        # Stretch remaining space
        self.grid_top.set_column_stretch(self.grid_top._auto_column)

        # Connect signals
        self.button_connect.signal_toggled.connect(self._button_connect_toggled)

        # Status
        self.label_status = self.grid_top.add(_g.Label(''))

        # Error
        self.grid_top.new_autorow()
        self.label_message = self.grid_top.add(_g.Label(''), column_span=10).set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')

        # By default the bottom grid is disabled
        self.grid_bot.disable()

        # Expand the bottom grid
        self.window.set_row_stretch(1)

        # Other data
        self.t0 = None

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=name)

        # Show the window.
        if show: self.window.show(block)

    def _button_connect_toggled(self, *a):
        """
        Connect by creating the API.
        """
        if self._api_class is None:
            raise Exception('You need to specify an api_class when creating a serial GUI object.')

        # If we checked it, open the connection and start the timer.
        if self.button_connect.is_checked():
            port = self.get_selected_port()
            self.api = self._api_class(
                    port=port,
                    address=self.number_address.get_value(),
                    baudrate=int(self.combo_baudrates.get_text()),
                    timeout=self.number_timeout.get_value())

            # If we're in simulation mode
            if self.api.simulation_mode:
                self.label_status.set_text('*** Simulation Mode ***')
                self.label_status.set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
                self.button_connect.set_colors(background='pink')
            else:
                self.label_status.set_text('Connected').set_colors('teal' if _s.settings['dark_theme_qt'] else 'blue')

            # Record the time if it's not already there.
            if self.t0 is None: self.t0 = _time.time()

            # Enable the grid
            self.grid_bot.enable()

            # Disable other controls
            self.combo_baudrates.disable()
            self.combo_ports.disable()
            self.number_timeout.disable()

        # Otherwise, shut it down
        else:
            self.api.disconnect()
            self.label_status.set_text('')
            self.button_connect.set_colors()
            self.grid_bot.disable()

            # Enable other controls
            self.combo_baudrates.enable()
            self.combo_ports.enable()
            self.number_timeout.enable()


        # User function
        self._after_button_connect_toggled()

    def _after_button_connect_toggled(self):
        """
        Dummy function called after connecting.
        """
        return

    def _new_exception(self, a):
        """
        Just updates the status with the exception.
        """
        self.label_message(str(a)).set_colors('red')

    def _window_close(self):
        """
        Disconnects. When you close the window.
        """
        print('Window closed but not destroyed. Use show() to bring it back.')
        if self.button_connect():
            print('  Disconnecting...')
            self.button_connect(False)

    def get_selected_port(self):
        """
        Returns the actual port string from the combo box.
        """
        return self._ports[self.combo_ports.get_index()]

class arduino_base_api():
    """
    Commands-only object for interacting with an Auber Instruments SYL-53X2P
    temperature controller.

    Parameters
    ----------
    port='COM3' : str
        Name of the port to connect to.

    baudrate=9600 : int
        Baud rate of the connection. Must match the instrument setting.

    timeout=2000 : number
        How long to wait for responses before giving up (ms). Must be >300 for this instrument.

    """
    def __init__(self, port='COM4', baudrate=9600, timeout=2000, **kwargs):

        # Check for installed libraries
        if not _serial:
            _s._warn('You need to install pyserial to use the Arduino.')
            self.serial = None
            self.simulation_mode = True

        # Assume everything will work for now
        else: self.simulation_mode = False

        # Also, if the specified port is "Simulation", enable simulation mode.
        if port=='Simulation': self.simulation_mode = True

        # Response from *IDN? query.
        self.idn = None


        # If we have all the libraries, try connecting.
        if not self.simulation_mode:
            try:

                # Create the instrument and ensure the settings are correct.
                self.serial = _serial.Serial(
                    port, baudrate=baudrate,
                    timeout=0.5) # HACK: temporarily short timeout to test for response

                # HACK: Keep trying until it's ready (temporarily disable the log)
                t0 = _time.time()
                log = self.log
                self.log = None
                while _time.time()-t0 < timeout*0.001 and self.idn==None:
                    self.idn = self.query('*IDN?', ignore_error=True)
                self.log = log

                # HACK: NOW set the desired timeout
                self.serial.timeout = timeout*0.001

                # Simulation mode flag
                self.simulation_mode = False

            # Something went wrong. Go into simulation mode.
            except Exception as e:
                print('Could not open connection to "'+port+'" at baudrate '+str(baudrate)+'. Entering simulation mode.')
                print(e)
                self.modbus = None
                self.serial = None
                self.simulation_mode = True

    def disconnect(self):
        """
        Disconnects.
        """
        if not self.simulation_mode: self.serial.close()

    def log(self, *a):
        """
        Overload this to change from printing all communications. You can
        also set it to False or None to disable.
        """
        print(*a)

    def write(self, message='*IDN?'):
        """
        Writes the message, adding the appropriate termination.

        Parameters
        ----------
        message='*IDN?' : str
            Message to send.
        """

        if self.log: self.log('arduino write', message)
        self.serial.write((message+'\n').encode())
        return self

    def read(self, return_type=str, ignore_error=False):
        """
        Reads until it receives a newline. Returns the stripped string.

        Parameters
        ----------
        return_type=str : function
            Function to convert to a desired resturn type (if no timeout).

        ignore_error=False : bool
            If True, will not raise an exception when it times out.
        """
        result = self.serial.readline()
        if len(result):
            result
            if self.log: self.log('arduino read', return_type, result.strip())
            return return_type(result.decode().strip())
        else:
            if self.log: self.log('arduino read', return_type, 'TIMEOUT')
            if not ignore_error: raise Exception('Arduino read timeout.')
            return None

    def query(self, message='*IDN?', return_type=str, ignore_error=False):
        """
        Calls a write(message) and read(). Returns None if it times out.

        Parameters
        ----------
        message='*IDN?' : str
            Query message.

        return_type=str : conversion function
            Function that converts the result to another type.

        ignore_error=False : bool
            If True, will not raise an exception when it times out.
        """
        x = self.serial.read_all()
        if len(x): print('RUH ROH: During query("'+message+'"), before write(), read_all() returned', x)
        self.write(message)
        return self.read(return_type, ignore_error)


class arduino_base():
    """
    Scripted graphical interface for an arduino.
    """
    def __init__(self, api_class=arduino_base_api, name='arduino',
                 show=True, block=False, window_size=[1,1]):

        # Run the base stuff
        self.serial_gui_base = serial_gui_base(api_class=api_class,
            name=name, show=show, block=block, window_size=window_size,
            hide_address=True)




if __name__ == '__main__':
    self = arduino_base()
