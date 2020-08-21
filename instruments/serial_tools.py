import spinmob.egg as _egg
import traceback as _traceback
_p = _traceback.print_last
_g = _egg.gui
import spinmob as _s
import time as _time

try: from serial.tools.list_ports import comports as _comports
except: _comports = None

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

    """
    def __init__(self, api_class=None, name='serial_gui', show=True, block=False, window_size=[1,1]):

        # Remebmer the name.
        self.name = name
        
        # Checks periodically for the last exception
        self.timer_exceptions = _g.ExceptionTimer()
       
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

        self._label_address = self.grid_top.add(_g.Label('Address:'))
        self.number_address = self.grid_top.add(_g.NumberBox(0, 1, int=True, autosettings_path=name+'.number_address', tip='Address (not used for every instrument)')).set_width(40)

        self._label_baudrate = self.grid_top.add(_g.Label('Baud:'))
        self.combo_baudrates = self.grid_top.add(_g.ComboBox(['1200', '2400', '4800', '9600', '19200'], autosettings_path=name+'.combo_baudrates'))

        self._label_timeout = self.grid_top.add(_g.Label('Timeout:'))
        self.number_timeout = self.grid_top.add(_g.NumberBox(2000, dec=True, bounds=(1, None), suffix=' ms', tip='How long to wait for an answer before giving up (ms).', autosettings_path=name+'.number_timeout')).set_width(100)

        # Button to connect
        self.button_connect  = self.grid_top.add(_g.Button('Connect', checkable=True))

        # Stretch remaining space
        self.grid_top.set_column_stretch(self.grid_top._auto_column)

        # Connect signals
        self.button_connect.signal_toggled.connect(self._button_connect_toggled)

        # Status
        self.label_status = self.grid_top.add(_g.Label(''))

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
            port = self._ports[self.combo_ports.get_index()]
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
                self.label_status.set_text('Connected')

            # Record the time if it's not already there.
            if self.t0 is None: self.t0 = _time.time()

            # Enable the grid
            self.grid_bot.enable()

        # Otherwise, shut it down
        else:
            self.api.disconnect()
            self.label_status.set_text('')
            self.button_connect.set_colors()
            self.grid_bot.disable()

        # User function
        self._after_button_connect_toggled()

    def _after_button_connect_toggled(self):
        """
        Dummy function called after connecting.
        """
        return
    
    def _window_close(self):
        """
        Disconnects. When you close the window.
        """
        print('Window closed but not destroyed. Use show() to bring it back.')
        if self.button_connect():
            print('  Disconnecting...')
            self.button_connect(False)
