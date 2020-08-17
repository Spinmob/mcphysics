import mcphysics   as _mp
import spinmob     as _s
import spinmob.egg as _egg
import numpy       as _n
import time        as _t
import os          as _os
_g  = _egg.gui
_gt = _mp.instruments._gui_tools
_p  = _mp._p

_debug=True
if _debug and _os.path.exists('debug_log.txt'): _os.remove('debug_log.txt')
def _debug_log(*a):
    a = list(a)
    if _debug and len(a):
        for n in range(len(a)): a[n] = str(a[n])
        line = ', '.join(a)
        f = open('debug_log.txt', 'a')
        f.write(line+'\n')
        f.close()
        print(line)

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
        self._thread_locker = _s.thread.locker()
        self._thread_shared_data = dict()

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
        self.grid_top.add(_g.Label('Buffer: '))
        self.number_buffer = self.grid_top.add(_g.NumberBox(0, int=True, bounds=(0,None), autosettings_path=name+'.number_buffer', tip='How big of an input / output buffer to use. Larger values increase latency, smaller values lead to discontinuities.\nZero means "optimal", which is different for different systems and sound cards.'))

        # Buttons
        self.button_record     = self.grid_top.add(_g.Button('Record', checkable=True))
        self.checkbox_overflow = self.grid_top.add(_g.CheckBox('Overflow      '))
        self.button_play       = self.grid_top.add(_g.Button('Play',   checkable=True))
        self.checkbox_underflow= self.grid_top.add(_g.CheckBox('Underflow     '))
        self.button_playrecord = self.grid_top.add(_g.Button('Play+Record')).set_width(110)
        self.button_stop       = self.grid_top.add(_g.Button('Stop')).disable()

        self.grid_top.add(_g.Label('    Status:'))
        self.button_stream  = self.grid_top.add(_g.Button('Stream'))
        self.number_threads = self.grid_top.add(_g.NumberBox(int=True))
        self.timer_status  = _g.Timer(100)
        self.timer_status.signal_tick.connect(self._timer_status_tick)

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
        self.tab_input.grid_trigger     = self.tab_input.tab_settings.add(_g.GridLayout(margins=False), alignment=0)
        self.tab_input.button_triggered = self.tab_input.grid_trigger.add(_g.Button('Idle', checkable=True), alignment=0)
        self.tab_input.button_force     = self.tab_input.grid_trigger.add(_g.Button('Force'))
        self.tab_input.button_force.signal_clicked.connect(self._button_force_clicked)

        self.tab_input.tab_settings.new_autorow()
        self.tab_input.settings = s = self.tab_input.tab_settings.add(_g.TreeDictionary(autosettings_path=name+'.tab_input.settings', name=name+'.tab_input.settings'), alignment=0)
        s.set_width(270)

        # AI Settings
        s.add_parameter('Iterations', 0, tip='Number of times to repeat the measurement. Set to 0 for infinite repetitions.')
        s.add_parameter('Rate', self._rates, default_list_index=4, tip='Sampling rate (Hz, synced with Samples and Time).')
        s.add_parameter('Samples', 1000.0, bounds=(1,    None), dec=True, siPrefix=True, suffix='S', tip='How many samples to record (synced with Rate and Time).')
        s.add_parameter('Time',       0.0, bounds=(1e-9, None), dec=True, siPrefix=True, suffix='s', tip='Duration of recording (synced with Rate and Samples).')
        s.add_parameter('Trigger', ['Continuous', 'Left', 'Right'], tip='Trigger Mode')
        s.add_parameter('Trigger/Level',      0.0,  step=0.01, bounds=(-1,1), tip='Trigger level')
        s.add_parameter('Trigger/Hysteresis', 0.01, step=0.01, bounds=(0,2),  tip='How far on the other side of the trigger the signal must go before retriggering is allowed.')
        s.add_parameter('Trigger/Mode', ['Rising Edge', 'Falling Edge'], tip='Trigger on the rising or falling edge.')
#        s.add_parameter('Trigger/Delay',      0.0,  suffix='s', siPrefix=True, tip='How long to wait after the trigger before keeping the data. Negative number means it will keep that much data before the trigger.')

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
        self.waveform_designer.after_settings_changed = self._after_waveform_changed

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
        self.tab_input.settings.connect_any_signal_changed(self._settings_changed_input)

        self.timer_status.start()

        # Show the window
        if show: self.window.show(block)

    def _after_waveform_changed(self):
        """
        After the settings change in the waveform designer.
        """
        # self._thread_locker.lock()

        # # Update the waveform
        # so = self.tab_output.settings
        # self._thread_shared_data['L'] = _n.array(self.pd['Left'],  dtype=_n.float32) * (1 if so['Left']  else 0)
        # self._thread_shared_data['R'] = _n.array(self.pd['Right'], dtype=_n.float32) * (1 if so['Left']  else 0)

        # self._thread_locker.unlock()

    def _button_force_clicked(self, *a):
        """
        Someone clicked "force" to force the trigger.
        """
        # Update the GUI and thread.
        self._thread_locker.lock()
        self._thread_shared_data['triggered'] = True
        self._thread_locker.unlock()

    def _button_play_toggled(self, *a):
        """
        Someone clicked "play".
        """
        self._thread_locker.lock()

        # Send signals to the thread
        self._thread_shared_data['button_play'] = self.button_play()

        if self.button_play.is_checked():

            self.button_play.set_colors(None, 'red')
            if not self.stream: self._start_stream()

        else: self.button_play.set_colors(None, None)

        self._thread_locker.unlock()
        # Otherwise we let it finish on its own.

    def _button_record_toggled(self, *a):
        """
        Someone pushed "record".
        """
        self._thread_locker.lock()

        # Send signals to the thread
        self._thread_shared_data['button_record'] = self.button_record()

        # We do special stuff when the record button is turned on.
        if self.button_record.is_checked():

            # We're starting over, so clear the stream.
            if self.stream: self.stream.read(self.stream.read_available)

            self.t_start     = _t.time()
            self.tab_input.number_iteration(1)
            self.tab_input.number_missed(0)
            self.button_record.set_colors(None, 'red')

            if not self.stream: self._start_stream()

        else:
            self.button_record.set_colors(None, None)
            self.tab_input.button_triggered(False).set_text('Idle').set_colors(None, None)

        self._thread_locker.unlock()

        # let it finish on its own.

    def _before_push_pull_thread(self):
        """
        Sets the appropriate state of things and pulls some data to thread-variables
        before starting the thread.

        This will always be called between threads, so should be safe.
        """
        # Update the state of the trigger button.
        if self.button_record():
            if self.tab_input.settings['Trigger'] == 'Continuous':
                self.tab_input.button_triggered(True).set_text('Continuous').set_colors('white','blue')
            else:
                self.tab_input.button_triggered(False).set_text('Waiting').set_colors('white','green')
        else: self.tab_input.button_triggered(False).set_text('Idle').set_colors(None, None)

        so = self.tab_output.settings

        # Store some thread variables
        self._thread_shared_data.update(dict(
            si        = self.tab_input.settings.get_dictionary(short_keys=True)[1],
            triggered = self.tab_input.button_triggered(),
            button_record = self.button_record(),
            button_play   = self.button_play(),
            L         = _n.array(self.pd['Left'],  dtype=_n.float32) * (1 if so['Left']  else 0),
            R         = _n.array(self.pd['Right'], dtype=_n.float32) * (1 if so['Right'] else 0),))


    def _push_pull_data(self):
        """
        Pushes the next block of data into the available output buffer, and
        pulls the next block of available data into the input buffer.
        """

        # This function is called in as separate thread at the beginning of
        # a new acquisition.

        # Set up the trigger buttons
        last_value = None # Used to catch index-0 triggers

        # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        self._thread_locker.lock()

        si = dict(self._thread_shared_data['si'])
        button_play = self._thread_shared_data['button_play']
        button_record = self._thread_shared_data['button_record']

        self._thread_locker.unlock()
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        # Reset the internal index and create a new buffer based on settings.
        ni = 0
        Ni = int(si['Samples'])
        buffer_in = _n.zeros((Ni,2), dtype=_n.float32)

        # Accumulate data until we're full (break out)
        while button_play or button_record:

            # We just lock each time through the loop to be safe / easy.
            # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
            self._thread_locker.lock()

            # Set this to True if we keep some data; used to decide what to do at the end.
            data_kept = False

            # If there is any room in the hardware buffer to write.
            if self.stream.write_available:

                # Bounds on what's available
                n1 = self._thread_shared_data['no']
                n2 = self._thread_shared_data['no']+self.stream.write_available

                # Get the arrays to send out
                L = _n.take(self._thread_shared_data['L'], range(n1,n2), mode='wrap')
                R = _n.take(self._thread_shared_data['R'], range(n1,n2), mode='wrap')

                # Write what's possible
                oops_out = self.stream.write(
                    _n.ascontiguousarray(
                        _n.array([L, R], dtype=_n.float32).transpose() ) )
                if oops_out: self._signal_output_underflow.emit(None)

                # Update the current index
                self._thread_shared_data['no'] = n2

            # If there is anything to read
            if self.stream.read_available:

                # Get the index range to read
                n1 = ni
                n2 = ni + self.stream.read_available # May as well be the latest number.

                # Make sure we don't go over the end of the array
                if n2 > Ni: n2 = Ni

                # Get what's available
                data, oops_in = self.stream.read(n2-n1)
                if oops_in: self._signal_input_overflow.emit(None)

                # If we're already triggered, collect the data
                if self._thread_shared_data['triggered']:
                    buffer_in[n1:n2] = data
                    data_kept = True

                # Otherwise, we're waiting and have to search for a trigger
                else:

                    # Index of the trigger event
                    i_trigger = None

                    # Map the correct channel of data to "rising edge" format
                    if si['Trigger/Mode'] == 'Falling Edge': sign = -1
                    else:                                    sign = 1
                    if si['Trigger'] == 'Right': a = sign*_n.array(data[:,1])
                    else:                        a = sign*_n.array(data[:,0])

                    # First see if the first data point is a trigger.
                    if  last_value is not None \
                    and last_value < sign*(si['Trigger/Level']-si['Trigger/Hysteresis']) \
                    and a[0] >= sign*si['Trigger/Level']:
                        i_trigger = 0

                    # Otherwise, do the "normal" trigger search
                    else:
                        i = _n.where(a < sign*(si['Trigger/Level']-si['Trigger/Hysteresis']))
                        if len(i[0]):
                            i0 = i[0][0]

                            # Look for first index above the level
                            i = _n.where(a[i0:] >= sign*si['Trigger/Level'])

                            # If we found one, update the index of the trigger.
                            if len(i[0]):
                                i_trigger = i0 + i[0][0]
                                n2 = n2 - i_trigger

                    # Otherwise, dump the data to the (reduced) buffer.
                    if i_trigger is not None:

                        # Push the button so we know to collect data for the next runs
                        self._thread_shared_data['triggered'] = True
                        self._signal_trigger_changed.emit('Triggered')

                        # Collect the reduced data set
                        buffer_in[n1:n2] = data[i_trigger:]
                        data_kept = True

                # End of "Normal" trigger search and data collection.

                # If the data was kept, update ni for the next loop or
                # quit if the buffer is full.
                if data_kept:

                    # If we're full or have stopped, break out; emits signal_done
                    if n2 == Ni:
                        self._signal_push_pull_done.emit(buffer_in)
                        self._thread_locker.unlock()
                        return

                    # Otherwise, update the bu for the next time through the loop.
                    else: ni = n2

            # Get the button status
            button_play   = self._thread_shared_data['button_play']
            button_record = self._thread_shared_data['button_record']

            # At the end of each iteration, unlock
            self._thread_locker.unlock()
            # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        # End of while loop

        # Data is invalid. Don't send it.
        self._signal_push_pull_done.emit(None)
        return

    def _push_pull_done(self, data):
        """
        A complete data set has been collected.
        """
        # Regardless of what we do with this data, we should fire off
        # a thread to collect more, because the buffers are hungry.
        if self.button_record.is_checked() or self.button_play.is_checked():
            self._before_push_pull_thread()
            _s.thread.start(self._push_pull_data)
        else:
            self.stream.stop()
            self.stream = None

            # Enable the sample rate again
            self.combo_rate.enable()
            self.combo_device.enable()
            self.number_buffer.enable()
            self.button_playrecord.enable()
            self.button_stop.disable()
            self.button_record.set_colors(None, None)
            self.button_play  .set_colors(None, None)
            self.tab_input.button_triggered(False).set_text('Idle').set_colors(None,None)

        # Now, if we're ready to process this data, do so.
        # This will be happening in parallel with the thread, so
        # make sure it doesn't touch _thread_shared_data or stream
        if self._ready_for_more_data and not data is None:
            self._ready_for_more_data = False

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

        # Otherwise, we haven't finished processing the previous data yet.
        elif not data is None:
            self.tab_input.number_missed.increment()
            self.checkbox_overflow(True)


    def _start_stream(self, *a):
        """
        Someone clicked "record".
        """

        # First run setup.
        self.combo_rate.disable()
        self.combo_device.disable()
        self.number_buffer.disable()
        self.button_stop.enable()
        self.checkbox_overflow.set_checked(False)
        self.checkbox_underflow.set_checked(False)

        # Ready for more data
        self._ready_for_more_data = True

        # Create and start the stream
        self._thread_shared_data['no'] = 0
        self.stream = self.api.Stream(
                samplerate         = float(self.tab_input.settings['Rate']),
                blocksize          = self.number_buffer(), # 0 for "optimal" latency
                channels           = 2,)

        # Create some signals the thread can send back to the GUI.
        self._signal_output_underflow = _s.thread.signal(self._event_output_underflow)
        self._signal_input_overflow   = _s.thread.signal(self._event_input_overflow)
        self._signal_trigger_changed  = _s.thread.signal(self._event_trigger_changed)
        self._signal_push_pull_done   = _s.thread.signal(self._push_pull_done)

        # Start a single data collection loop.
        # This feeds hungry buffers and pulls into a buffer, so we set it on its own thread.
        # Before starting, update some gui stuff, and pull some data into
        # thread-safe variables. The thread should not be accessing GUI elements.
        self._before_push_pull_thread()
        self.stream.start()
        _s.thread.start(self._push_pull_data)


    def _event_output_underflow(self, *a):
        """
        Called when there is an output underflow event.
        """
        self.checkbox_underflow(True)

    def _event_input_overflow(self, *a):
        """
        Called when there is an input overflow event.
        """
        self.checkbox_overflow(True)

    def _event_trigger_changed(self, a):
        """
        Called when the trigger state changes in the thread. Only updates the GUI.
        """
        # Update the GUI based on the incoming data from the thread.
        if   a == 'Triggered'  : self.tab_input.button_triggered(True).set_text('Triggered') .set_colors('white', 'red')
        elif a == 'Continuous' : self.tab_input.button_triggered(True).set_text('Continuous').set_colors('white', 'blue')
        elif a == 'Waiting'    : self.tab_input.button_triggered(True).set_text('Waiting')   .set_colors('white', 'green')
        elif a == 'Idle'       : self.tab_input.button_triggered(True).set_text('Idle')      .set_colors(None, None)

    def _button_playrecord_clicked(self, *a):
        """
        Just pushes both.
        """
        self.button_play(True)
        self.button_record(True)


    def _button_stop_clicked(self, *a):
        """
        Just stops both.
        """
        self.button_play(False)
        self.button_record(False)

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

    def _settings_changed_input(self, *a):
        """
        Settings changed
        """
        self._thread_locker.lock()

        if len(a):
            self._sync_rates_samples_time(a[0].name())

            # If we set the trigger to continuous and are running, Trigger.
            if  a[0].name() == 'Trigger' \
            and self.stream:
                if a[0].value() == 'Continuous':
                    self.tab_input.button_triggered(True).set_text('Continuous').set_colors('white','blue')
                else:
                    self.tab_input.button_triggered(False).set_text('Waiting').set_colors('white', 'green')

        self._thread_shared_data['si'] = self.tab_input.settings.get_dictionary()[1]
        self._thread_locker.unlock()

    def _timer_status_tick(self, *a):
        """
        Updates the status of the inner workings.
        """
        if self.stream: self.button_stream(True).set_colors('white', 'green')
        else:           self.button_stream(False).set_colors(None, None)

        self.number_threads(_s.thread.pool.activeThreadCount())

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


