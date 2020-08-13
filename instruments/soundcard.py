import mcphysics   as _mp
import spinmob.egg as _egg
import numpy       as _n
_g  = _egg.gui
_gt = _mp.instruments._gui_tools
_p  = _mp._p

class soundcard():
    """
    Scripted graphical interface for a sound card.

    Parameters
    ----------
    name='soundcard' : str
        Unique identifier for the app. Mostly useful for the autosettings_paths.
    """
    def __init__(self, name='soundcard', show=True, block=False):

        self.name = name
        self._rates = [44100, 48000, 96000, 192000]

        # Make sure we have the library
        if _mp._sounddevice is None:
            _mp.spinmob._warn('You need to install the sounddevice python library to use soundcard_api.')

            # We're in simulation mode.
            self.simulation_mode = True

            # No direct API
            self.api = None

        else:

            # We're not in simulation mode
            self.simulation_mode = False

            # Expose the API
            self.api = _mp._sounddevice


        # Main Layout
        self.window = _g.Window('Soundcard', autosettings_path=name+'.window')
        self.grid_top = self.window.add(_g.GridLayout(margins=False))
        self.window.new_autorow()
        self.tabs = self.window.add(_g.TabArea(autosettings_path=name+'.tabs'), alignment=0)

        # Top controls

        # Combo device selector
        device_names = self.get_device_names() + ['Simulation']
        self.combo_devices = self.grid_top.add(_g.ComboBox(device_names, autosettings_path=name+'.combo_devices'))
        self.label_rate    = self.grid_top.add(_g.Label('Rate (Hz):'))
        self.combo_rate    = self.grid_top.add(_g.ComboBox(self._rates,  autosettings_path=name+'.combo_rate'))
        if not self.simulation_mode:

            # Match the input and output devices and update the list.
            self.set_output_device(self.get_selected_input_device_index())
            self.combo_devices.set_index(self.get_selected_input_device_index())

        # Link the signal
        self.combo_devices.signal_changed.connect(self._combo_devices_changed)
        self.combo_rate   .signal_changed.connect(self._combo_rate_changed)

        # Buttons
        self.button_record     = self.grid_top.add(_g.Button('Record'))
        self.button_play       = self.grid_top.add(_g.Button('Play'))
        self.button_playrecord = self.grid_top.add(_g.Button('Play+Record')).set_width(110)
        self.button_stop       = self.grid_top.add(_g.Button('Stop'))

        self.button_record    .signal_clicked.connect(self._button_record_clicked)
        self.button_play      .signal_clicked.connect(self._button_play_clicked)
        self.button_playrecord.signal_clicked.connect(self._button_playrecord_clicked)
        self.button_stop      .signal_clicked.connect(self._button_stop_clicked)

        # AI tab
        self.tab_input = self.tabs.add_tab('Input')
        self.tab_input.tabs_settings = self.tab_input.add(_g.TabArea(autosettings_path=name+'.tab_input.tabs_settings'))
        self.tab_input.tab_settings  = self.tab_input.tabs_settings.add_tab('Input Settings')
        self.tab_input.settings = s  = self.tab_input.tab_settings.add(_g.TreeDictionary(autosettings_path=name+'.tab_input.settings', name=name+'.tab_input.settings'), alignment=0)

        # AI Settings
        s.add_parameter('Iterations', 1, tip='Number of times to repeat the measurement. Set to 0 for infinite repetitions.')
        s.add_parameter('Rate', self._rates, tip='Sampling rate (Hz).')
        s.add_parameter('Samples', 1000.0, bounds=(1,None), dec=True, siPrefix=True, suffix='S', tip='How many samples to record.')

        s.connect_signal_changed('Rate', self._input_rate_changed)

        # Aliases and shortcuts
        self.signal_chain = self.sc = self.tab_input.add(_gt.signal_chain(name+'.tabs_ai_plots'), alignment=0)
        self.plot_raw = self.tab_input.plot_raw = self.pr = self.signal_chain.plot_raw
        self.A1       = self.tab_input.A1       = self.signal_chain.A1
        self.A2       = self.tab_input.A2       = self.signal_chain.A2
        self.A3       = self.tab_input.A3       = self.signal_chain.A3
        self.B1       = self.tab_input.B1       = self.signal_chain.B1
        self.B2       = self.tab_input.B2       = self.signal_chain.B2
        self.B3       = self.tab_input.B3       = self.signal_chain.B3
        self.tab_input.set_column_stretch(1)

        # AO tab
        self.tab_output = self.tabs.add_tab('Output')
        self.waveform_designer = self.wd = self.tab_output.add(
            _gt.waveform_designer(channels=['L','R'],
                                  rates=self._rates,
                                  name=name+'.waveform_designer',
                                  sync_rates=True,
                                  sync_samples=True),
            alignment=0)
        self.waveform_designer.add_channel('Left')
        self.waveform_designer.add_channel('Right')

        # aliases and shortcuts
        self.plot_design = self.pd = self.tab_output.plot_design = self.waveform_designer.plot_design
        self.tab_output.settings = self.waveform_designer.settings


        # Show the window
        if show: self.window.show(block)

    def _button_play_clicked(self, *a):
        """
        Someone toggled play.
        """
        self.api.play(_n.array([self.pd['Left'], self.pd['Right']]).transpose(),
                      samplerate=self.waveform_designer.get_rate('Left'))

    def _button_record_clicked(self, *a):
        """
        Someone clicked "record".
        """
        s = self.tab_input.settings
        R = float(s['Rate'])
        N = int(s['Samples'])
        vs = self.api.rec(N, samplerate=R, channels=2)
        self.api.wait()

        # Generate the time array
        self.pr['t']     = _n.linspace(0,(N-1)/R,N)
        self.pr['Left']  = vs[:,0]
        self.pr['Right'] = vs[:,1]
        self.pr.plot()
        self.window.process_events()

        self.signal_chain.process_data()

        return

    def _button_playrecord_clicked(self, *a):
        si = self.tab_input.settings
        Ri = float(si['Rate'])

        # Play and record
        vs = self.api.playrec(_n.array([self.pd['Left'], self.pd['Right']]).transpose(),
                              samplerate=self.waveform_designer.get_rate('Left'),
                              channels=2)
        self.api.wait()

        # Generate the time array
        Ni = len(vs[:,0])
        self.pr['t']     = _n.linspace(0,(Ni-1)/Ri,Ni)
        self.pr['Left']  = vs[:,0]
        self.pr['Right'] = vs[:,1]
        self.pr.plot()
        self.window.process_events()

        self.signal_chain.process_data()


        return

    def _button_stop_clicked(self, *a): self.api.stop()

    def _combo_devices_changed(self, *a):
        """
        Called when someone changes the device.
        """
        if not self.combo_devices.get_value() == 'Simulation':
            self.set_devices(self.combo_devices.get_index(), self.combo_devices.get_index())

    def get_devices(self):
        """
        Returns a list of device objects. (DeviceList object)
        """
        return self.api.query_devices()

    def get_device_names(self):
        """
        Returns a list of device names.
        """
        ds = self.get_devices()
        names = []
        for n in range(len(ds)): names.append(ds[n]['name'])
        return names

    def get_selected_input_device(self):
        """
        Returns the selected input device object.
        """
        if not self.simulation_mode: return self.get_devices()[self.api.default.device[0]]

    def get_selected_input_device_index(self):
        """
        Returns the index of the currently selected input device.
        """
        return self.api.default.device[0]

    def get_selected_output_device_index(self):
        """
        Returns the index of the currently selected output device.
        """
        return self.api.default.device[1]

    def get_selected_output_device(self):
        """
        Returns the selected input device object.
        """
        if not self.simulation_mode: return self.get_devices()[self.api.default.device[1]]

    def set_input_device(self, device=None):
        """
        If an integer is supplied, sets the input device.
        """
        if not device is None: self.api.default.device[0] = device
        return self

    def set_output_device(self, device=None):
        """
        If an integer is supplied, sets the output device.
        """
        if not device is None: self.api.default.device[1] = device
        return self

    def set_devices(self, input_device=None, output_device=None):
        """
        Sets either or both input and output devices, if specified as integers.
        """
        self.set_input_device(input_device)
        self.set_output_device(output_device)
        return self

    def set_device(self, device=None):
        """
        Sets both input and output to the same device.
        """
        self.set_devices(device,device)


if __name__ == '__main__':
    self = soundcard()