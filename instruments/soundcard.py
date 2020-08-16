import mcphysics   as _mp
import spinmob     as _s
import spinmob.egg as _egg
import numpy       as _n
import time        as _t
import os          as _os
_g  = _egg.gui
_gt = _mp.instruments._gui_tools
_p  = _mp._p

if _os.path.exists('log.txt'): _os.remove('log.txt')
def _log(s):
    f = open('log.txt', 'a')
    f.write(s+'\n')
    f.close()
    print(s)

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
        self._rates = [8000, 11025, 22050, 32000, 44100, 48000, 96000, 192000]
        self.stream = None

        # Make sure we have the library
        if _mp._sounddevice is None:
            raise Exception('You need to install the sounddevice python library to use soundcard_api.')

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
        self.combo_device = self.grid_top.add(_g.ComboBox(device_names, autosettings_path=name+'.combo_device'))
        self.label_rate    = self.grid_top.add(_g.Label('Rate (Hz):'))
        self.combo_rate    = self.grid_top.add(_g.ComboBox(self._rates,  autosettings_path=name+'.combo_rate'))

        # Match the input and output devices and update the list.
        self.set_output_device(self.get_selected_input_device_index())
        self.combo_device.set_index(self.get_selected_input_device_index())

        # Link the signal
        self.combo_device.signal_changed.connect(self._combo_device_changed)
        self.combo_rate   .signal_changed.connect(self._combo_rate_changed)

        # Buffer
        self.label_buffer  = self.grid_top.add(_g.Label('Buffer: '))
        self.number_buffer = self.grid_top.add(_g.NumberBox(0, int=True, bounds=(0,None), autosettings_path=name+'.number_buffer', tip='How big of an input / output buffer to use. Larger values increase latency, smaller values lead to discontinuities.\nZero means "optimal", which is different for different systems and sound cards.'))

        # Buttons
        self.button_record     = self.grid_top.add(_g.Button('Record', checkable=True))
        self.checkbox_overflow = self.grid_top.add(_g.CheckBox('Overflow      '))
        self.button_play       = self.grid_top.add(_g.Button('Play',   checkable=True))
        self.checkbox_underflow= self.grid_top.add(_g.CheckBox('Underflow     '))
        self.button_playrecord = self.grid_top.add(_g.Button('Play+Record')).set_width(110)
        self.button_stop       = self.grid_top.add(_g.Button('Stop'))

        self.button_record    .signal_toggled.connect(self._button_record_toggled)
        self.button_play      .signal_toggled.connect(self._button_play_toggled)
        self.button_playrecord.signal_clicked.connect(self._button_playrecord_clicked)
        self.button_stop      .signal_clicked.connect(self._button_stop_clicked)

        # AI tab
        self.tab_input = self.tabs.add_tab('Input')
        self.tab_input.tabs_settings = self.tab_input.add(_g.TabArea(autosettings_path=name+'.tab_input.tabs_settings'))
        self.tab_input.tab_settings  = self.tab_input.tabs_settings.add_tab('Input Settings')

        self.tab_input.grid_controls    = self.tab_input.tab_settings.add(_g.GridLayout(margins=False))
        self.tab_input.label_iteration  = self.tab_input.grid_controls.add(_g.Label('Iteration:'))
        self.tab_input.number_iteration = self.tab_input.grid_controls.add(_g.NumberBox(0, int=True))
        self.tab_input.label_missed     = self.tab_input.grid_controls.add(_g.Label('Missed:'))
        self.tab_input.number_missed    = self.tab_input.grid_controls.add(_g.NumberBox(0, int=True))

        self.tab_input.tab_settings.new_autorow()
        self.tab_input.settings = s  = self.tab_input.tab_settings.add(_g.TreeDictionary(autosettings_path=name+'.tab_input.settings', name=name+'.tab_input.settings'), alignment=0)
        s.set_width(250)

        # AI Settings
        s.add_parameter('Iterations', 0, tip='Number of times to repeat the measurement. Set to 0 for infinite repetitions.')
        s.add_parameter('Rate', self._rates, default_list_index=4, tip='Sampling rate (Hz, synced with Samples and Time).')
        s.add_parameter('Samples', 1000.0, bounds=(1,    None), dec=True, siPrefix=True, suffix='S', tip='How many samples to record (synced with Rate and Time).')
        s.add_parameter('Time',       0.0, bounds=(1e-9, None), dec=True, siPrefix=True, suffix='s', tip='Duration of recording (synced with Rate and Samples).')

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
        self.waveform_designer.settings.add_parameter('Loop', True, tip='Whether to loop this or play it once.')
        self.waveform_designer.add_channel('Left')
        self.waveform_designer.add_channel('Right')

        # aliases and shortcuts
        self.plot_design = self.pd = self.tab_output.plot_design = self.waveform_designer.plot_design
        self.tab_output.settings = self.waveform_designer.settings


        # Hide the Rates (they're controlled by the top combo) and sync
        self.tab_input .settings.hide_parameter('Rate')
        self.tab_output.settings.hide_parameter('Left/Rate')
        self.tab_output.settings.hide_parameter('Right/Rate')
        self._combo_rate_changed()

        # Sync everything
        self._sync_rates_samples_time('Samples')

        # Connect signals
        self.tab_input.settings.connect_any_signal_changed(self._tab_input_settings_changed)

        # Show the window
        if show: self.window.show(block)

    def _button_play_toggled(self, *a):
        """
        Someone clicked "play".
        """
        if self.button_play.is_checked():

            self.button_play.set_colors(None, 'red')
            if not self.stream: self._start_stream()

        else: self.button_play.set_colors(None, None)

        # Otherwise we let it finish on its own.

    def _button_record_toggled(self, *a):
        """
        Someone pushed "record".
        """
        # We do special stuff when the record button is turned on.
        if self.button_record.is_checked():

            # We're starting over, so clear the stream.
            if self.stream:
                _log(str(self.stream.read_available))
                self.stream.read(self.stream.read_available)

            self.t_start     = _t.time()
            self.t_collected = 0
            self.tab_input.number_iteration(1)
            self.tab_input.number_missed(0)
            self.button_record.set_colors(None, 'red')

            if not self.stream: self._start_stream()

        else: self.button_record.set_colors(None, None)

        # Otherwise we let it finish on its own.

    def _push_pull_data(self):
        """
        Pushes the next block of data into the available output buffer, and
        pulls the next block of available data into the input buffer.
        """
        # New input buffer
        self._ni = 0
        self._buffer_in = _n.zeros((int(self.tab_input.settings['Samples']),2)) # Initial Buffer.

        # Output buffer is created elsewhere.

        # Accumulate data until we're full (break out)
        while True:

            # If there is any room in the hardware buffer to write.
            if self.stream.write_available: self._push_available()

            # If there is anything to read
            if self.stream.read_available:

                # Get the index range to read
                n1 = self._ni
                n2 = self._ni + self.stream.read_available
                Ni = len(self._buffer_in)

                # Make sure we don't go over the end of the array
                if n2 > Ni: n2 = Ni

                # Get what's available
                data, oops_in = self.stream.read(n2-n1)
                if oops_in:
                    print('Warning: Input Overflow')
                    self.checkbox_overflow(True)

                # Stick it in our buffer
                self._buffer_in[n1:n2] = data

                # If we're full, break out.
                if n2 == Ni: break

                # Otherwise, prep for the next one.
                else: self._ni = n2

    def _push_available(self):
        """
        Pushes the next block to the available buffer.
        """
        # Bounds on what's available
        n1 = self._no
        n2 = self._no+self.stream.write_available

        # Get the arrays to send out
        L = _n.take(self.pd['Left'],  range(n1,n2), mode='wrap')
        R = _n.take(self.pd['Right'], range(n1,n2), mode='wrap')

        # Write what's possible
        oops_out = self.stream.write(
            _n.ascontiguousarray(
                _n.array([L, R], dtype=_n.float32).transpose() ) )
        if oops_out:
            print('Warning: Output Underflow')
            self.checkbox_underflow(True)

        # Update the current index
        self._no = n2

    def _push_pull_done(self, *a):
        """
        Data set collected.
        """
        # If we're ready for more data,
        if self._ready_for_more_data:
            self._ready_for_more_data = False # This is for future threads to look at.

            # This is for us locally.
            data = _n.array(self._buffer_in)

            # Increment the number of iterations.
            self.tab_input.number_iteration.increment()

        # Otherwise, we have to skip this data!
        else:
            data = None
            self.tab_input.number_missed.increment()
            self.checkbox_overflow(True)

        # Regardless of what we do with this data, we should still fire off
        # A thread to collect more, because the buffer is so hungry.
        if self.button_record.is_checked() or self.button_play.is_checked():
            _s.thread.start(self._push_pull_data, done=self._push_pull_done)
        else:
            self.stream.stop()
            self.stream = None

            # Enable the sample rate again
            self.combo_rate.enable()
            self.combo_device.enable()
            self.number_buffer.enable()
            self.button_playrecord.enable()
            self.button_record.set_colors(None, None)
            self.button_play  .set_colors(None, None)

        # Now, if we're supposed to process this data, do so.
        if not data is None:

            # Generate the time array
            Ni = len(data)
            R  = float(self.combo_rate.get_text())
            self.pr['t']     = _n.linspace(0,(Ni-1)/R,Ni)
            self.pr['Left']  = data[:,0]
            self.pr['Right'] = data[:,1]

            # Plot autosave and run the signal analysis chain.
            self.pr.plot()
            self.pr.autosave()
            self.signal_chain.run()

            # Reset the ready flag
            self._ready_for_more_data = True

    def _stream_callback(self, indata, outdata, frames, time, status):
        """
        Called automatically by a running stream whenever it has and requires
        data.
        """
        if self.button_play() or self.button_record():

            # OUTPUT DATA

            # Bounds
            n1 = self._no
            n2 = self._no+frames

            # Overwrite the elements of the supplied output buffer.
            outdata[:,0] = _n.take(self.pd['Left'],  range(n1,n2), mode='wrap')
            outdata[:,1] = _n.take(self.pd['Right'], range(n1,n2), mode='wrap')

            # Update the current index
            self._no = n2


            # INPUT DATA

            # Special case: self._ni == 0 means we need to create our input buffer
            if self._ni == 0:

                # Create the buffer.
                self._buffer_in = _n.zeros((int(self.tab_input.settings['Samples']),2), dtype=_n.float32)

                # If there is a tail, pre-concatenate with incoming data
                if not self._buffer_tail is None:
                    indata = _n.concatenate((self._buffer_tail, indata))
                    frames = len(indata)
                    self._buffer_tail = None

            # Get the index range to readk for our OWN buffer
            n1 = self._ni
            n2 = self._ni + frames
            Ni = len(self._buffer_in)

            # Make sure we don't go over the end of the array
            if n2 > Ni:

                # Set the max to our max.
                n2 = Ni

                # Save the tail!
                self._buffer_tail = indata[n2:]

            # Stick it in our buffer
            self._buffer_in[n1:n2] = indata[0:n2-n1]

            # If we're full, send a signal to take it.
            if n2 == Ni: self.stream.signals.done.emit(_n.array(self._buffer_in))

            # Otherwise, prep for the next one.
            else: self._ni = n2


        # Everything is unchecked. Tell it to stop.
        elif self.stream:
            self.stream.stop()
            self.stream = None




    def _start_stream(self, *a):
        """
        Someone clicked "record".
        """
        # First run setup.
        self.combo_rate.disable()
        self.combo_device.disable()
        self.number_buffer.disable()
        self.button_playrecord.disable()
        self.checkbox_overflow.set_checked(False)
        self.checkbox_underflow.set_checked(False)

        # Create and start the stream
        self._no = 0 # Output current index
        self._ni = 0 # Input current index
        self._ready_for_more_data = True
        #self._buffer_tail = None
        self.stream = self.api.Stream(
                samplerate         = float(self.tab_input.settings['Rate']),
                blocksize          = self.number_buffer(), # 0 for "optimal" latency
                channels           = 2,)
                #callback           = self._stream_callback)
        #self.stream.signals = _s.thread._signals()
        #self.stream.signals.done.connect(self._push_pull_done)
        self.stream.start()

        # Start a collection. This involves hungry buffers so we set it on its own thread.
        _s.thread.start(self._push_pull_data, done=self._push_pull_done)

    def _button_playrecord_clicked(self, *a):
        si = self.tab_input.settings
        Ri = float(si['Rate'])
        N  = len(self.pd['Left'])

        vs = self.api.playrec(_n.array([self.pd['Left'], self.pd['Right']]).transpose(),
                              samplerate=self.waveform_designer.get_rate('Left'),
                              channels=2)
        self.api.wait()

        # Generate the time array
        self.pr['t']     = _n.linspace(0,(N-1)/Ri,N)
        self.pr['Left']  = vs[:,0]
        self.pr['Right'] = vs[:,1]
        self.pr.plot()
        self.window.process_events()

        self.signal_chain.process_data()


        return

    def _button_stop_clicked(self, *a): self.api.stop()

    def _combo_device_changed(self, *a):
        """
        Called when someone changes the device.
        """
        if not self.combo_device.get_value() == 'Simulation':
            self.set_devices(self.combo_device.get_index(), self.combo_device.get_index())

    def _combo_rate_changed(self, *a):
        """
        Called when someone changes the rate.
        """
        self.tab_input.settings['Rate']       = self.combo_rate.get_text()
        self.tab_output.settings['Left/Rate'] = self.combo_rate.get_text()

    def _sync_rates_samples_time(self, key):
        """
        Syncs the Rate, Samples, and Time based on what changed.
        """
        # If we get a Rate, Samples, or Time, update the others
        if key in ['Rate', 'Samples', 'Time']:
            s = self.tab_input.settings

            # If Rate or Time changed, set the number of samples, rounding
            if key in ['Rate', 'Time']: s.set_value('Samples', _n.ceil(s['Time'] * float(s['Rate'])), block_key_signals=True)

            # Make sure the time matches the rounded samples (or changed samples!)
            s.set_value('Time', s['Samples'] / float(s['Rate']), block_key_signals=True)

    def _tab_input_settings_changed(self, *a):
        """
        Settings changed
        """
        if len(a):
            self._sync_rates_samples_time(a[0].name())

            # Flush the buffer if we switch continuous mode
            if a[0].name() == 'Continuous': self.stream.read(self.stream.read_available) # Flush buffer.


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
        return self.get_devices()[self.api.default.device[0]]

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
        return self.get_devices()[self.api.default.device[1]]

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
    #_g.clear_egg_settings()
    self = soundcard()




    # sd =_mp._sounddevice

    # # import sounddevice as _sd
    # import numpy as np
    # stream = sd.Stream(
    #             samplerate         = 48000,
    #             blocksize          = 10000, #self.number_buffer(), # 0 for "optimal" latency
    #             channels           = 2,)
    # stream.start()

    # for n in range(100):
    #     print('Output Step', n, stream.write_available)

    #     if stream.write_available:
    #         stream.write(np.ascontiguousarray(0.1*np.random.rand(stream.write_available, 2), dtype=np.float32))


