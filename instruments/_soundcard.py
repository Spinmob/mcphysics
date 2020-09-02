import mcphysics   as _mp
import spinmob     as _s
import spinmob.egg as _egg
import numpy       as _n
import time        as _t
import os          as _os
_g  = _egg.gui
try:    from . import _gui_tools as _gt
except: _gt = _mp.instruments._gui_tools
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

        self._exception_timer = _g.TimerExceptions()

        # All data accessed by the push-pull thread lives in this dictionary.
        # If you're using this dictionary, make sure to lock the thread!
        self._shared = dict()
        self._shared['stream'] = None
        self._thread_locker = _s.thread.locker()

        # Make sure we have the library
        if _mp._sounddevice is None:
            raise Exception('You need to install the sounddevice python library to use soundcard_api.')

        # Expose the API
        self.api = _mp._sounddevice

        # Main Layout
        self.window = _g.Window('Soundcard', autosettings_path=name+'.window')
        self.window.event_close = self._event_close

        self.grid_top = self.window.add(_g.GridLayout(margins=False), alignment=0)
        self.window.new_autorow()
        self.tabs = self.window.add(_g.TabArea(autosettings_path=name+'.tabs'), alignment=0)

        # Top controls

        # Combo device selector
        device_names = self.get_device_names()
        self.grid_top.add(_g.Label('Input:'))
        self.combo_device_in = self.grid_top.add(_g.ComboBox(
            device_names, autosettings_path=name+'.combo_device_in'))
        self.grid_top.add(_g.Label('Rate (Hz):'))
        self.combo_rate_in = self.grid_top.add(_g.ComboBox(
            self._rates,  autosettings_path=name+'.combo_rate_in',
            default_index=4))

        # Buffer
        self.grid_top.add(_g.Label('Buffer: '))
        self.number_buffer = self.grid_top.add(_g.NumberBox(0, int=True, bounds=(0,None), autosettings_path=name+'.number_buffer', tip='How big of an input / output buffer to use. Larger values increase latency, smaller values lead to discontinuities.\nZero means "optimal", which is different for different systems and sound cards.'))

        # Buttons
        self.button_record = self.grid_top.add(_g.Button(
            'Record', checkable=True,
            signal_toggled = self._button_record_toggled))

        self.checkbox_overflow = self.grid_top.add(_g.CheckBox('Overflow  '))

        self.button_play = self.grid_top.add(_g.Button(
            'Play', checkable=True,
            signal_toggled = self._button_play_toggled))

        self.checkbox_underflow= self.grid_top.add(_g.CheckBox('Underflow  '))

        self.button_playrecord = self.grid_top.add(_g.Button(
            'Play+Record', checkable=True,
            signal_toggled = self._button_playrecord_toggled)).set_width(110)

        self.grid_top.set_column_stretch(self.grid_top._auto_column)
        self.grid_top._auto_column += 1

        self.grid_top.add(_g.Label('  Status:'))
        self.button_stream  = self.grid_top.add(_g.Button(
            'Stream', tip='Whether the audio stream is active.').set_width(70))
        self.number_threads = self.grid_top.add(_g.NumberBox(
            0, int=True, tip='Number of running threads.').set_width(40))
        self.timer_status  = _g.Timer(100, signal_tick=self._timer_status_tick)

        # Next row
        self.grid_top.new_autorow()
        self.grid_top.add(_g.Label('Output: '))
        self.combo_device_out = self.grid_top.add(_g.ComboBox(device_names, autosettings_path=name+'.combo_device_out'))
        self.grid_top.add(_g.Label('Rate (Hz):'))
        self.combo_rate_out = self.grid_top.add(_g.ComboBox(
            self._rates,  autosettings_path=name+'.combo_rate_out',
            default_index=4))

        # Link the signals
        self.combo_device_out.signal_changed.connect(self._combo_device_changed)
        self.combo_rate_out  .signal_changed.connect(self._combo_rate_changed)
        self.combo_device_in .signal_changed.connect(self._combo_device_changed)
        self.combo_rate_in   .signal_changed.connect(self._combo_rate_changed)

        # # Match the input and output devices and update the list.
        # self.set_output_device(self.get_selected_input_device_index())
        # self.combo_device_out.set_index(self.get_selected_input_device_index())



        # AI tab
        self.tab_in = self.tabs.add_tab('Input')
        self.tab_in.tabs_settings = self.tab_in.add(_g.TabArea(autosettings_path=name+'.tab_in.tabs_settings'))
        self.tab_in.tab_settings  = self.tab_in.tabs_settings.add_tab('Input Settings')

        self.tab_in.grid_controls    = self.tab_in.tab_settings.add(_g.GridLayout(margins=False))
        self.tab_in.label_iteration  = self.tab_in.grid_controls.add(_g.Label('Iteration:'))
        self.tab_in.number_iteration = self.tab_in.grid_controls.add(_g.NumberBox(0, int=True))
        self.tab_in.label_missed     = self.tab_in.grid_controls.add(_g.Label('Missed:'))
        self.tab_in.number_missed    = self.tab_in.grid_controls.add(_g.NumberBox(0, int=True))

        self.tab_in.tab_settings.new_autorow()
        self.tab_in.grid_trigger     = self.tab_in.tab_settings.add(_g.GridLayout(margins=False), alignment=0)
        self.tab_in.button_triggered = self.tab_in.grid_trigger.add(_g.Button(
            text = 'Idle', checkable=True,
            signal_toggled = self._button_triggered_toggled), alignment=0)

        self.tab_in.tab_settings.new_autorow()
        self.tab_in.settings = s = self.tab_in.tab_settings.add(_g.TreeDictionary(
            autosettings_path  = name+'.tab_in.settings',
            name               = name+'.tab_in.settings',
            new_parameter_signal_changed = self._settings_changed_input), alignment=0)
        s.set_width(270)

        # AI Settings
        s.add_parameter('Iterations', 0, tip='Number of times to repeat the measurement. Set to 0 for infinite repetitions.')
        s.add_parameter('Rate', self._rates, default_list_index=4, tip='Sampling rate (Hz, synced with Samples and Time).')
        s.add_parameter('Samples', 1000.0, bounds=(2,    None), dec=True, siPrefix=True, suffix='S', tip='How many samples to record (synced with Rate and Time).')
        s.add_parameter('Time',       0.1, bounds=(1e-9, None), dec=True, siPrefix=True, suffix='s', tip='Duration of recording (synced with Rate and Samples).')
        s.add_parameter('Trigger', ['Continuous', 'Left', 'Right'], tip='Trigger Mode')
        s.add_parameter('Trigger/Level',      0.0,  step=0.01, bounds=(-1,1), tip='Trigger level')
        s.add_parameter('Trigger/Hysteresis', 0.0, step=0.01, bounds=(0,2), tip='How far on the other side of the trigger the signal must go before retriggering is allowed.')
        s.add_parameter('Trigger/Mode', ['Rising Edge', 'Falling Edge'], tip='Trigger on the rising or falling edge.')
        s.add_parameter('Trigger/Stay_Triggered', False, tip='After triggering, remain triggered to collect continuous data thereafter.')
#        s.add_parameter('Trigger/Delay',      0.0,  suffix='s', siPrefix=True, tip='How long to wait after the trigger before keeping the data. Negative number means it will keep that much data before the trigger.')

        # Aliases and shortcuts
        self.data_processor    = self.tab_in.data_processor = self.tab_in.add(_gt.data_processor(name+'.tabs_ai_plots'), alignment=0)
        self.tab_in.plot_raw = self.data_processor.plot_raw
        self.tab_in.A1       = self.tab_in.A1       = self.data_processor.A1
        self.tab_in.A2       = self.tab_in.A2       = self.data_processor.A2
        self.tab_in.A3       = self.tab_in.A3       = self.data_processor.A3
        self.tab_in.B1       = self.tab_in.B1       = self.data_processor.B1
        self.tab_in.B2       = self.tab_in.B2       = self.data_processor.B2
        self.tab_in.B3       = self.tab_in.B3       = self.data_processor.B3
        self.tab_in.set_column_stretch(1)

        # AO tab
        self.tab_out = self.tabs.add_tab('Output')
        self.waveform_designer = self.tab_out.waveform_designer = self.tab_out.add(
            _gt.waveform_designer(rates=self._rates,
                                  name=name+'.waveform_designer',
                                  sync_rates=True,
                                  sync_samples=True),
            alignment=0)
        self.waveform_designer.add_channels('Left','Right')

        # aliases and shortcuts
        self.tab_out.plot_design = self.waveform_designer.plot_design
        self.tab_out.settings    = self.waveform_designer.settings

        # Hide the Rates (they're controlled by the top combo) and sync
        self.tab_in .settings.hide_parameter('Rate')
        self.tab_out.settings.hide_parameter('Left/Rate')
        self.tab_out.settings.hide_parameter('Right/Rate')
        self._combo_rate_changed()
        self._combo_device_changed()

        # Sync everything
        self._sync_rates_samples_time('Samples')



        # QUADRATURES TAB

        self.tab_quad = self.tabs.add_tab('Quadratures')

        self.quadratures = self.tab_quad.quadratures = self.tab_quad.add(_gt.quadratures(
            channels = ['Left', 'Right'],
            name = name+'.quadratures'), alignment=0)

        # Loop button is overkill
        self.quadratures.button_loop.hide()

        # Signals
        self.quadratures.button_sweep.signal_toggled.connect(self._button_sweep_frequency_toggled)
        self.quadratures.button_get_raw.signal_toggled.connect(self._button_quad_get_raw_toggled)

        # Modify the existing buttons because this system is so weird.
        self.quadratures.button_get_raw.set_checkable(True).set_text('Get Data')
        self.quadratures.button_get_raw.signal_toggled.connect(self._button_quad_get_raw_toggled)
        self.quadratures.get_raw = lambda *a : None  # Kill the fake data.

        # Sweep signals
        self.signal_sweep_iterate  = _s.thread.signal(self._sweep_iterate)
        self.signal_waveform_ok    = _s.thread.signal(self._sweep_waveform_ok)
        self.signal_quad_new_data  = _s.thread.signal(self._quad_new_data)
        self.signal_sweep_done     = _s.thread.signal(self._sweep_done)

        # Fix the units
        self._strip_V_suffix(self.tab_out.settings)

        # Start the timer
        self.timer_status.start()

        # Show the window
        if show: self.window.show(block)

    def _strip_V_suffix(self, s):
        """
        Loops over keys and eliminates all 'V' suffixes.
        """
        for k in s.get_keys():
            o = s.get_pyqtgraph_options(k)
            if 'suffix' in o and o['suffix'] == 'V':
                s.set_pyqtgraph_options(k, suffix='')


    def _event_close(self, *a):
        """
        Called when the window closes.
        """
        print('Stopping soundcard and closing window, but not destroying. Use self.window.show() to bring it back.')
        self.quadratures.button_sweep(False)
        self.button_playrecord(False)
        self.button_play(False)
        self.button_record(False)

    def _button_quad_get_raw_toggled(self, *a):
        """
        Someone toggles the get_raw button.
        """
        # Make sure the record button is clicked.
        self.button_record(self.quadratures.button_get_raw())

    def _button_sweep_frequency_toggled(self, *a):
        """
        When someone toggles "Sweep".
        """
        # Start the process.
        if self.quadratures.button_sweep():
            self.quadratures.button_sweep.set_colors('white', 'green')
            self.signal_sweep_iterate.emit((0,0))
        else:
            self.signal_sweep_done.emit(None)

    def _sweep_iterate(self, a):
        """
        Performs one iteration and increments the counter.

        n is the zero-referenced step, and i is the zero-referenced
        iteration at this step.

        """
        # Unpack the data
        n, i = a

        # Shortcuts
        q = self.quadratures

        # If we're done.
        if n >= q.settings['Sweep/Steps'] or not q.button_sweep():
            q.button_sweep(False).set_colors(None, None)
            return

        # Update the user; we do iteration after data comes in.
        I = self.quadratures.number_step(n+1)
        self.quadratures.number_iteration_sweep(i+1)

        # We only have to set up the output and let it settle
        # if we're starting a new frequency
        if i > 0:
            self.quadratures.button_get_raw(True)
            return

        # Get the current target frequency
        f_target = self.quadratures.get_sweep_step_frequency(I())

        # Shortcuts
        pd = self.quadratures.plot_raw
        sd = self.quadratures.settings
        so = self.tab_out.settings
        si = self.tab_in.settings

        # Clear the raw plot and start over.
        pd.clear()

        # Setup the output waveform without emitting signals.
        output_settings = {
            'Left/Waveform'        : 'Sine',
            'Left/Sine'            : f_target,
            'Left/Sine/Phase'      : 90,
            'Left/Sine/Amplitude'  : sd['Output/Left_Amplitude'],

            'Right/Waveform'       : 'Sine',
            'Right/Sine/Phase'     : 90,
            'Right/Sine/Amplitude' : sd['Output/Right_Amplitude'],

            'Left' : True,
            'Right': True,
            'Left/Loop'  : True,
            'Right/Loop' : True,
            }
        so.update(output_settings, block_key_signals=True)

        # Calculate and update the rest of the settings.
        self.waveform_designer.update_other_quantities_based_on('Left/Sine')
        so.set_value('Right/Sine/Cycles', so['Left/Sine/Cycles'], block_key_signals=True)

        # Update the design and plot.
        self._thread_locker.lock()
        self.waveform_designer.update_design()
        self._thread_locker.unlock()

        # Update the ACTUAL quadrature frequency
        f = so['Left/Sine']
        self.quadratures.number_frequency(f)

        # Figure out how many samples we need to have a integer number of periods AND be larger
        # than our collect time.
        if f:
            periods            = _n.ceil(sd['Input/Collect']*f) # Number of periods to span our collection time.
            samples_per_period = float(self.combo_rate_in.get_text())/f
            samples = _n.round(periods*samples_per_period)
        else:
            samples = _n.round(float(self.combo_rate_in.get_text())*sd['Input/Collect'])

        si['Iterations'] = 0
        si['Samples'] = samples
        si['Trigger'] = 'Continuous'

        # Uncheck auto mode (handled by Get Raw button)
        self.quadratures.checkbox_auto(False)

        # If we haven't started yet, start playing
        self.button_play(True)

        # Tell it to look for a new waveform. It will emit a signal when it gets this.
        self._set_shared(new_waveform = True)


    def _sweep_waveform_ok(self, a):
        """
        Signal emitted when the thread receives the new waveform and will begin
        buffering it.
        """
        # Wait for the settle time, but only on the first iteration
        self.window.sleep(self.quadratures.settings['Input/Settle'])

        # Now start collecting.
        self.quadratures.button_get_raw(True)

    def _quad_new_data(self, a):
        """
        Called when the input has new data to get the quadratures from.
        """
        data, underflow, overflow, get_quadratures = a

        # If there was an error, retry the point.
        if underflow or overflow:
            self.signal_sweep_iterate.emit(
                (self.quadratures.number_step()-1, self.quadratures.number_iteration_sweep()-1))
            return

        # Otherwise, it's valid, so analyze.

        # Shortcuts
        pr = self.tab_in.plot_raw
        pd = self.quadratures.plot_raw
        I  = self.quadratures.number_iteration_sweep
        S  = self.quadratures.number_step

        # Clear and import the header
        pd.clear()
        pd.copy_headers_from(pr)

        # Copy the columns in the right fashion (time-signal pairs)
        for k in pr.ckeys[1:]:
            pd['t_'+k] = pr['t']
            pd[k]  = pr[k]

        pd.plot().autosave()

        # Run the quadrature calculation
        if get_quadratures: self.quadratures.button_get_quadratures.click()

        # Turn off record and reset the trigger
        self.quadratures.button_get_raw(False)

        # Next frequency
        if I() >= self.quadratures.settings['Input/Iterations']:
            I(0)
            self.signal_sweep_iterate.emit((S(), I()))

        # Next iteration
        else: self.signal_sweep_iterate.emit((S()-1, I()))

    def _sweep_done(self, a):
        """
        Called when the sweep is done.
        """
        # Shut it down.
        self.quadratures.button_sweep(False).set_colors(None, None)
        self.button_playrecord(False)
        self.button_play(False)
        self.button_record(False)



    # def _wait_for_new_waveform(self, timeout=3):
    #     """
    #     Sends the message new_waveform = True to the thread and waits for it
    #     to turn False.

    #     Returns True if timeout.
    #     """
    #     self._set_shared(new_waveform = True)
    #     t0 = _t.time()
    #     while self._get_shared('new_waveform', bool) and _t.time()-t0 < timeout:
    #         _t.sleep(0.25)
    #         self.window.process_events()

    #     # Return the timeout status.
    #     return self._get_shared('new_waveform', bool)

    def _button_play_toggled(self, *a):
        """
        Someone clicked "play".
        """
        self._thread_locker.lock()

        # Send signals to the thread
        self._shared['button_play'] = self.button_play()

        if self.button_play.is_checked():

            self.button_play.set_colors('white', 'red')
            if not self._shared['stream']: self._start_stream()

        else: self.button_play.set_colors(None, None)

        self._thread_locker.unlock()
        # Otherwise we let it finish on its own.

    def _button_record_toggled(self, *a):
        """
        Someone pushed "record".
        """
        self._thread_locker.lock()

        # Send signals to the thread
        self._shared['button_record'] = self.button_record()

        # We do special stuff when the record button is turned on.
        if self.button_record():

            # We're starting over, so clear the stream if it exists.
            if self._shared['stream']:
                self._shared['stream'].read(self._shared['stream'].read_available)
                self._shared['abort'] = True

            # Otherwise start the stream.
            else: self._start_stream()

            self.button_record.set_colors('white', 'red')

        else: self.button_record.set_colors(None, None)

        self._thread_locker.unlock()

        # let it finish on its own.

    def _button_playrecord_toggled(self, *a):
        """
        Just pushes both.
        """
        self.button_play  (self.button_playrecord())
        self.button_record(self.button_playrecord())

        if self.button_playrecord(): self.button_playrecord.set_colors('white', 'red')
        else:                        self.button_playrecord.set_colors(None, None)

    def _before_thread_push_pull(self, stay_triggered=False):
        """
        Sets the appropriate state of things and pulls some data to thread-variables
        before starting the thread.

        This will always be called between threads, so should be safe.
        """
        si = self.tab_in.settings
        so = self.tab_out.settings

        # Update the state of the trigger button.
        bt = self.tab_in.button_triggered
        if si['Trigger'] == 'Continuous':
            bt(True).set_text('Continuous').set_colors('white','blue')
        elif self._shared['triggered'] and stay_triggered:
            bt(True).set_text('Locked').set_colors('white','red')
        else:
            bt(False).set_text('Waiting').set_colors('white','green')

        # Store some thread variables
        self._shared.update(dict(
            underflow     = False,
            overflow      = False,
            abort         = False,
            si            = self.tab_in.settings.get_dictionary(short_keys=True)[1],
            triggered     = self.tab_in.button_triggered(),
            trigger_type  = si['Trigger'],
            button_record = self.button_record(),
            button_play   = self.button_play(),
            L         = _n.array(self.tab_out.plot_design['Left'],  dtype=_n.float32) * (1 if so['Left']  and self.button_play() else 0),
            R         = _n.array(self.tab_out.plot_design['Right'], dtype=_n.float32) * (1 if so['Right'] and self.button_play() else 0),))


    def _thread_push_pull(self):
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

        button_play   = self._shared['button_play']
        button_record = self._shared['button_record']

        # Reset the internal index and create a new buffer based on settings.
        ni = 0
        Ni = int(self._shared['si']['Samples'])
        buffer_in = _n.zeros((Ni,2), dtype=_n.float32)
        underflow = False
        overflow  = False

        # Prevent slowdown for large index
        self._shared['no'] = self._shared['no'] % len(self._shared['L'])

        # If we changed the waveform, let the world know we have it.
        if 'new_waveform' in self._shared.keys() and self._shared['new_waveform']:
            self._shared['new_waveform'] = False
            self.signal_waveform_ok.emit(None)

        self._thread_locker.unlock()
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        # Push and pull data until we've collected a full data set.
        # Note we always push and pull even if play or record are disabled
        # At a factor-of-two-ish performance hit level, we keep the input
        # and output synchronized, eliminating the need for a trigger channel!
        while button_play or button_record:

            # We just lock each time through the loop to be safe / easy.
            # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
            self._thread_locker.lock()

            si = self._shared['si']

            # Set this to True if we keep some data; used to decide what to do at the end.
            data_kept = False

            # If there is any room in the hardware buffer to write.
            if self._shared['stream'].write_available:

                # Bounds on what's available
                n1 = self._shared['no']
                n2 = self._shared['no']+self._shared['stream'].write_available

                # Wrap slows down for big indices.
                L = _n.take(self._shared['L'], range(n1,n2), mode='wrap')
                R = _n.take(self._shared['R'], range(n1,n2), mode='wrap')

                # Write what's possible
                oops_out = self._shared['stream'].write(
                    _n.ascontiguousarray(
                        _n.array([L, R], dtype=_n.float32).transpose() ) )
                if oops_out:
                    underflow = self._shared['underflow'] = True
                    self._signal_output_underflow.emit(None)

                # Update the current index
                self._shared['no'] = n2

            # If there is anything to read
            if self._shared['stream'].read_available:

                # Get the index range to read
                n1 = ni
                n2 = ni + self._shared['stream'].read_available # May as well be the latest number.

                # Make sure we don't go over the end of the array
                if n2 > Ni: n2 = Ni

                # Get what's available
                data, oops_in = self._shared['stream'].read(n2-n1)
                if oops_in:
                    overflow = self._shared['overflow'] = True
                    self._signal_input_overflow.emit(None)

                # If we're already triggered, collect the data
                if self._shared['triggered'] \
                or self._shared['trigger_type'] == 'Continuous' \
                or not button_record:
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
                        self._shared['triggered'] = True
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
                        self._signal_push_pull_done.emit(
                            (buffer_in, underflow, overflow) if button_record and not self._shared['abort'] else None)
                        self._thread_locker.unlock()
                        return

                    # Otherwise, update the bu for the next time through the loop.
                    else: ni = n2

            # Get the button status
            button_play   = self._shared['button_play']
            button_record = self._shared['button_record']

            # At the end of each iteration, unlock
            self._thread_locker.unlock()
            # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        # End of while loop

        # Data is invalid. Don't send it.
        self._signal_push_pull_done.emit(None)
        return

    def _push_pull_done(self, a):
        """
        A complete data set has been collected.
        """

        # Regardless of what we do with this data, we should fire off
        # a thread to collect more, because the buffers are hungry.
        si = self.tab_in.settings
        if self.button_record.is_checked() or self.button_play.is_checked():
            self._before_thread_push_pull(
                stay_triggered = si['Trigger/Stay_Triggered'] and self._shared['triggered'])
            _s.thread.start(self._thread_push_pull, priority=2)
        else:
            self._shared['stream'].stop()
            self._shared['stream'] = None

            self._unlock_controls()


        # Now, if we're ready to process this data, do so.
        # This will be happening in parallel with the thread, so
        # make sure it doesn't touch _thread_shared_data or stream
        if self._ready_for_more_data and not a is None:

            (data, underflow, overflow) = a

            self._ready_for_more_data = False

            self.tab_in.number_iteration.increment()

            # Generate the time array
            Ni = len(data)
            R  = float(self.combo_rate_in.get_text())
            self.tab_in.plot_raw['t']     = _n.linspace(0,(Ni-1)/R,Ni)
            self.tab_in.plot_raw['Left']  = data[:,0]
            self.tab_in.plot_raw['Right'] = data[:,1]

            # Plot autosave and run the signal analysis chain.
            self.tab_in.plot_raw.plot()
            self.tab_in.plot_raw.autosave()
            self.data_processor.run()

            # If we're running a sweep, send the data to the quadratures raw
            # We also send the sweep state to indicate whether that function
            # should automatically get the quadratures.
            if self.quadratures.button_get_raw() or self.quadratures.checkbox_auto():
                self.signal_quad_new_data.emit(
                    (data, underflow, overflow, self.quadratures.button_sweep() or self.quadratures.checkbox_auto()))

            # If we've hit the iteration limit, uncheck record
            if self.tab_in.number_iteration() >= self.tab_in.settings['Iterations'] \
            and not self.tab_in.settings['Iterations'] == 0:
                self.button_playrecord(False)
                self.button_record(False)
                self.button_play(False)

            # Otherwise get the next data.
            else: self._ready_for_more_data = True

        # Otherwise, we haven't finished processing the previous data yet.
        else: self.tab_in.number_missed.increment()

    def _unlock_controls(self):
        """
        Reenables buttons etc.
        """
        # Enable the sample rate again
        self.combo_rate_in.enable()
        self.combo_rate_out.enable()
        self.combo_device_out.enable()
        self.combo_device_in.enable()
        self.number_buffer.enable()
        self.tab_in.button_triggered(False, block_signals=True).set_text('Idle').set_colors(None,None)
        self.button_playrecord(False)
        self.button_record(False)
        self.button_play  (False)

    def _start_stream(self, *a):
        """
        Someone clicked "record".
        """

        # First run setup.
        self.combo_rate_in.disable()
        self.combo_rate_out.disable()
        self.combo_device_out.disable()
        self.combo_device_in.disable()
        self.number_buffer.disable()
        self.checkbox_overflow.set_checked(False)
        self.checkbox_underflow.set_checked(False)

        self.t_start = _t.time()
        self.tab_in.number_iteration(0)
        self.tab_in.number_missed(0)

        # Ready for more data
        self._ready_for_more_data = True

        # Create and start the stream
        self._shared['no'] = 0
        self._shared['triggered'] = False
        try:
            self._shared['stream'] = self.api.Stream(
                    samplerate         = float(self.tab_in.settings['Rate']),
                    blocksize          = self.number_buffer(), # 0 for "optimal" latency
                    channels           = 2,)
        except Exception as e:
            print(e)
            self._unlock_controls()
            return

        # Create some signals the thread can send back to the GUI.
        self._signal_output_underflow = _s.thread.signal(self._event_output_underflow)
        self._signal_input_overflow   = _s.thread.signal(self._event_input_overflow)
        self._signal_trigger_changed  = _s.thread.signal(self._event_trigger_changed)
        self._signal_push_pull_done   = _s.thread.signal(self._push_pull_done)

        # Start a single data collection loop.
        # This feeds hungry buffers and pulls into a buffer, so we set it on its own thread.
        # Before starting, update some gui stuff, and pull some data into
        # thread-safe variables. The thread should not be accessing GUI elements.
        self._before_thread_push_pull()
        self._shared['stream'].start()
        _s.thread.start(self._thread_push_pull, priority=2)


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
        if   a == 'Triggered'  : self.tab_in.button_triggered(True).set_text('Triggered') .set_colors('white', 'red')
        elif a == 'Continuous' : self.tab_in.button_triggered(True).set_text('Continuous').set_colors('white', 'blue')
        elif a == 'Waiting'    : self.tab_in.button_triggered(False).set_text('Waiting')   .set_colors('white', 'green')
        elif a == 'Idle'       : self.tab_in.button_triggered(False).set_text('Idle')      .set_colors(None, None)

    def _button_triggered_toggled(self, *a):
        """
        When someone toggles the trigger.
        """
        self._set_shared(triggered = self.tab_in.button_triggered())

        # Update the GUI
        si = self.tab_in.settings
        if self.button_record() or self.button_play():
            if   si['Trigger'] == 'Continuous': self._event_trigger_changed('Continuous')
            elif self.tab_in.button_triggered(): self._event_trigger_changed('Triggered')
            else:                                   self._event_trigger_changed('Waiting')
        else:
            self._event_trigger_changed('Idle')

    def _combo_device_changed(self, *a):
        """
        Called when someone changes the device.
        """
        self.set_devices(
            self.combo_device_in .get_index(),
            self.combo_device_out.get_index())

    def _combo_rate_changed(self, *a):
        """
        Called when someone changes the rate.
        """
        self.tab_in .settings['Rate']      = self.combo_rate_in .get_text()
        self.tab_out.settings['Left/Rate'] = self.combo_rate_out.get_text()

    def _sync_rates_samples_time(self, key):
        """
        Syncs the Rate, Samples, and Time based on what changed.
        """
        # If we get a Rate, Samples, or Time, update the others
        if key in ['Rate', 'Samples', 'Time']:
            s = self.tab_in.settings

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
            and self._shared['stream']:
                if a[0].value() == 'Continuous':
                    self.tab_in.button_triggered(True).set_text('Continuous').set_colors('white','blue')
                else:
                    self.tab_in.button_triggered(False).set_text('Waiting').set_colors('white', 'green')

        self._shared['si'] = self.tab_in.settings.get_dictionary(short_keys=True)[1]
        self._thread_locker.unlock()

    def _set_shared(self, **kwargs):
        """
        Sets shared values in a thread-safe way.
        """
        self._thread_locker.lock()
        self._shared.update(kwargs)
        self._thread_locker.unlock()

    def _get_shared(self, key, return_type):
        """
        Returns a copy of an object from self._shared in a thread-safe way.

        Returns None if the key doesn't exist.

        return_type is the function that does the copying, e.g. int.
        """
        self._thread_locker.lock()
        x = return_type(self._shared[key]) if key in self._shared.keys() else None
        self._thread_locker.unlock()
        return x


    def _timer_status_tick(self, *a):
        """
        Updates the status of the inner workings.
        """
        self._thread_locker.lock()

        if self._shared['stream']: self.button_stream(True).set_colors('white', 'green')
        else:            self.button_stream(False).set_colors(None, None)

        self.number_threads(_s.thread.pool.activeThreadCount())

        self._thread_locker.unlock()

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


