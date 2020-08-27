import numpy   as _n
import time    as _time
import spinmob as _s
import spinmob.egg as _egg
_g = _egg.gui
import mcphysics as _mp

_debug_enabled = False
_debug = _mp._debug
_p = _mp._p

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
            _time.sleep(0.4)
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
            self.button_acquire(False)
            return

        # Ask the user for the dump file
        self.path = _s.dialogs.save('*.csv', 'Select an output file.', force_extension='*.csv')
        if self.path == None:
            self.button_acquire(False)
            return

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
        self.api._t0 = _time.time()
        self._dump(['Date:', _time.ctime()], 'w')
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


if __name__ == '__main__':
    self = keithley_dmm()