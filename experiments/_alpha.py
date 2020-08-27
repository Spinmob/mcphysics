# -*- coding: utf-8 -*-

import mcphysics as _mp
import numpy as _n
import spinmob.egg as _egg
import traceback as _traceback
_p = _traceback.print_last
_g = _egg.gui
import spinmob as _s
import time as _time

try:    from . import serial_tools as _serial_tools
except: _serial_tools = _mp.instruments._serial_tools

_mp._debug_enabled = True
_debug = _mp._debug


class alpha_arduino(_serial_tools.arduino_base):
    """
    Class for talking to the Arduino used to control the Alpha experiments.

    Parameters
    ----------
    name='alpha_arduino' : str
        Distinctive name for this instance. Used for remembering egg_settings, and other
        settings.

    enable_conversion_edit=False : bool
        Set to True to enable editing of the conversion parameters. Use this option, but
        do so with some level of caution. If the bias scale gets edited, for example,
        you can accidentally overbias the detector. Another option is to adjust these manually
        with, e.g., self.conversion['Pirani/V_offset'] = new_value.

    block=False
        Whether to block the console while the window is open.
    """

    def __init__(self, name='alpha_arduino', enable_conversion_edit=False, block=False):

        number_width = 80

        # Run the base arduino stuff
        _serial_tools.arduino_base.__init__(self, name=name, show=False)

        # Shortcuts
        self.label_status   = self.serial_gui_base.label_status
        self.label_message  = self.serial_gui_base.label_message
        self.button_connect = self.serial_gui_base.button_connect
        self.window         = self.serial_gui_base.window



        #####################################
        ## Tab area
        self.serial_gui_base.grid_bot.new_autorow()
        self.tabs = self.serial_gui_base.grid_bot.add(_g.TabArea(
            autosettings_path=name+'.tabs'), alignment=0)
        self.tab_cal = self.tabs.add_tab('"Meaningful" Values')
        self.tab_raw = self.tabs.add_tab('Arduino Values')


        ###################################
        ## RAW TAB
        self.grid_raw_state = self.tab_raw.add(_g.GridLayout(margins=False))

        #### ROW 1

        self.grid_raw_state.add(_g.Label('ADC1:'), alignment=2)
        self.number_adc1 = self.grid_raw_state.add(_g.NumberBox(
            value=0, step=0.1, bounds=(0,3.3), decimals=4, suffix='V',
            autosettings_path=name+'.number_adc1',
            tip='Nominal voltage at ADC1 (bias readout); 0-3.3V.')).disable().set_width(number_width)

        self.grid_raw_state.add(_g.Label('PWM1:'), alignment=2)
        self.number_pwm1_setpoint = self.grid_raw_state.add(_g.NumberBox(
            value = 0.0, step = 0.1, bounds = (0,3.3), decimals=4, suffix='V',
            autosettings_path = name+'.number_pwm1_setpoint',
            tip               = 'Setpoint for PWM1 (bias setpoint); 0-3.3V.',
            signal_changed    = self._number_pwm1_setpoint_changed,
            )).set_width(number_width)

        self.button_pwm1_enabled = self.grid_raw_state.add(_g.Button(
            'Disabled', checkable=True,
            tip='Whether to enable the bias output.',
            signal_toggled = self._button_bias_enabled_toggled
            )).set_colors('white', 'blue')

        self.grid_raw_state.add(_g.Label('Software PWM1 Upper Limit:'))
        self.number_pwm1_limit = self.grid_raw_state.add(_g.NumberBox(
            value = 1.263, bounds=(0,2.165), decimals=4, step=0.02,
            autosettings_path = name+'.number_pwm1_limit',
            signal_changed=self._number_pwm1_limit_changed,
            tip='Software upper bound on the PWM1 setpoint, to prevent accidentally setting to too large a value.\n'
               +'You can adjust this, but be careful. It is probably better to adjust the limit on the other tab.'
            )).set_width(number_width)

        #### ROW 2

        self.grid_raw_state.new_autorow()
        self.grid_raw_state.add(_g.Label('ADC2:'), alignment=2)
        self.number_adc2 = self.grid_raw_state.add(_g.NumberBox(
            value=0, step=0.1, bounds=(0,3.3), decimals=4, suffix='V',
            autosettings_path=name+'.number_adc2',
            tip='Voltage at ADC2 (pirani readout); 0-3.3V.')).disable().set_width(number_width)

        self.grid_raw_state.add(_g.Label('PWM2:'), alignment=2)
        self.number_pwm2_setpoint = self.grid_raw_state.add(_g.NumberBox(
            value=0.0, step=0.01, bounds=(0,3.3), decimals=4, suffix='V',
            autosettings_path = name+'.number_pwm2_setpoint',
            tip               = 'Setpoint for PWM2 (vent valve setpoint); 0-3.3V.',
            signal_changed    = self._number_pwm2_setpoint_changed
            )).set_width(number_width)

        #### ROW 3

        self.grid_raw_state.new_autorow()
        self.grid_raw_state.add(_g.Label('ADC3:'), alignment=2)
        self.number_adc3 = self.grid_raw_state.add(_g.NumberBox(
            value=0, step=0.1, bounds=(0,3.3), decimals=4, suffix='V',
            autosettings_path=name+'.number_adc3',
            tip='Voltage at ADC3 (pressure transducer); 0-3.3V.')).disable().set_width(number_width)

        self.grid_raw_state.add(_g.Label('Pump Valve:'), alignment=2)
        self.button_pump_valve_raw = self.grid_raw_state.add(_g.Button(
            'Closed', checkable=True,
            autosettings_path = name+'.button_pump_valve_raw',
            signal_toggled    = self._button_pump_valve_raw_toggled,
            tip='Whether the pump valve relay is open or closed.'
            )).set_colors('white','blue')

        # Plot raw
        self.tab_raw.new_autorow()

        # self.button_raw_show_plot = self.tab_raw.add(_g.Button(
        #     '^^^^^^^', checkable=True, checked=True,
        #     autosettings_path = name+'.button_raw_show_plot',
        #     signal_toggled    = self._button_raw_show_plot_toggled,
        #     tip='Show / hide the plot.'), alignment=0)

        # self.tab_raw.new_autorow()

        self.tab_raw.plot = self.tab_raw.add(_g.DataboxPlot(
            autosettings_path = name+'.tab_raw.plot',
            name              = name+'.tab_raw.plot',
            show_logger       = True), alignment=0)



        ####################################
        ## CAL TAB

        self.grid_cal_state = self.tab_cal.add(_g.GridLayout(margins=False), column_span=2)

        ####### BIAS

        #self.grid_cal_state.add(_g.Label('BIAS')).set_style(header_style)

        self.grid_cal_state.add(_g.Label('Bias Setpoint:'), alignment=2)
        self.number_bias_setpoint = self.grid_cal_state.add(_g.NumberBox(
            value=0.0, step=1, bounds=(0,70), decimals=4, suffix='V',
            autosettings_path=name+'.number_bias_setpoint',
            signal_changed=self._number_bias_setpoint_changed,
            tip='Detector bias voltage setpoint.')).set_width(number_width)

        self.grid_cal_state.add(_g.Label('Measured:'), alignment=2)
        self.number_bias_measured = self.grid_cal_state.add(_g.NumberBox(
            decimals=4,
            autosettings_path=name+'.number_bias_measured',
            tip='Measured bias voltage based on ADC1 and conversion parameters.')).disable().set_width(number_width)

        self.button_bias_enabled = self.grid_cal_state.add(_g.Button(
            'Disabled', checkable=True,
            tip = 'Enable the bias output.',
            signal_toggled = self._button_bias_enabled_toggled
            )).set_colors('white','blue')

        self.grid_cal_state.add(_g.Label('Software Upper Limit:'))
        self.number_bias_limit = self.grid_cal_state.add(_g.NumberBox(
            value=70.0, step=1, bounds=(0,120), decimals=4, suffix='V',
            autosettings_path=name+'.number_bias_limit',
            signal_changed=self._number_bias_limit_changed,
            tip='Software upper bound on the bias setpoint, to help prevent accidentally setting it too high.\n'+
                'You can change this, but be careful!'
            )).set_width(number_width)

        self.grid_cal_state.new_autorow()

        ####### PRESSURE

        #self.grid_cal_state.add(_g.Label('PRESSURE')).set_style(header_style)

        self.grid_cal_state.add(_g.Label('Pressure Transducer:'), alignment=2)
        self.number_pressure_transducer = self.grid_cal_state.add(_g.NumberBox(
            value=0, step=0.1, bounds=(0,None), decimals=4, suffix='Pa', siPrefix=True,
            autosettings_path=name+'.number_pressure_transducer',
            tip='Pressure measured by the transducer. Relies on conversion parameters.')).disable().set_width(number_width)

        self.grid_cal_state.add(_g.Label('Pirani:'), alignment=2)
        self.number_pressure_pirani = self.grid_cal_state.add(_g.NumberBox(
            value=0, step=0.1, bounds=(0,None), decimals=4, suffix='Pa', siPrefix=True,
            autosettings_path=name+'.number_pirani',
            tip='Pressure measured by the Pirani gauge. Relies on conversion parameters.')).disable().set_width(number_width)

        self.grid_cal_state.new_autorow()

        ####### VALVES

        #self.grid_cal_state.add(_g.Label('VALVES')).set_style(header_style)

        self.grid_cal_state.add(_g.Label('Pump Valve:'), alignment=2)
        self.button_pump_valve_cal = self.grid_cal_state.add(_g.Button(
            'Closed', checkable=True,
            autosettings_path = name+'.button_pump_valve_cal',
            signal_toggled    = self._button_pump_valve_cal_toggled,
            tip='Whether the pump valve is open or closed.'
            )).set_colors('white','blue')

        self.grid_cal_state.add(_g.Label('Vent Valve:'), alignment=2)
        self.number_vent_valve_setpoint = self.grid_cal_state.add(_g.NumberBox(
            value=0.0, step=0.01, bounds=(0,100), decimals=4, suffix='%',
            autosettings_path=name+'.number_vent_valve_setpoint',
            signal_changed = self._number_vent_valve_setpoint_changed,
            tip='Vent valve setpoint (0-100%).')).set_width(number_width)


        # Plot raw
        self.tab_cal.new_autorow()

        # Settings
        sr = self.conversion = self.tab_cal.settings = self.tab_cal.add(_g.TreeDictionary(
            autosettings_path = name+'.tab_cal.settings',
            name              = name+'.tab_cal.settings',
            new_parameter_signal_changed=self._settings_cal_changed)).set_width(230)

        if not enable_conversion_edit: sr.disable()

        sr.add('Bias/V_bias:V_PWM1', 55.44, suffix='V/V',
               tip='Ratio of volts applied to the detection circuit (above the big resistor) to volts from the Arduino PWM1.')

        sr.add('Bias/V_bias:V_ADC1', 80.0, suffix='V/V',
               tip='Ratio of volts applied to the detection circuit (above the big resistor) to volts measured at the Arduino ADC1.')


        sr.add('Pirani/P_offset', 0.0, suffix='Pa', siPrefix=True,
               tip='Pressure (Pa) = P_offset + P_scale * 10**((V_ADC2-V_offset)/V_scale)')

        sr.add('Pirani/P_scale', 1.0, suffix='Pa', siPrefix=True,
               tip='Pressure (Pa) = P_offset + P_scale * 10**((V_ADC2-V_offset)/V_scale)')

        sr.add('Pirani/V_offset', 3.5, suffix='V',
               tip='Pressure (Pa) = P_offset + P_scale * 10**((V_ADC2-V_offset)/V_scale)')

        sr.add('Pirani/V_scale', 1.0, suffix='V',
               tip='Pressure (Pa) = P_offset + P_scale * 10**((V_ADC2-V_offset)/V_scale)')


        sr.add('Pressure_Transducer/P_offset', 0.0, suffix='Pa', siPrefix=True,
               tip='Pressure (Pa) = P_offset + Ratio*V_ADC3')

        sr.add('Pressure_Transducer/Ratio', 38200.0, suffix='Pa/V', siPrefix=True,
               tip='Pressure (Pa) = P_offset + Ratio*V_ADC3')


        sr.add('Vent_Valve/Scale', 5.0, suffix='%/V',
               tip='Overall scale factor.\nPercentage Open = Scale*(V_PWM2 * Gain_LPF - V_offset)')

        sr.add('Vent_Valve/Gain_LPF', 6.783,
               tip='Gain from the (active) low-pass filter on the PWM output.\nPercentage Open = Scale*(V_PWM2 * Gain_LPF - V_offset)')

        sr.add('Vent_Valve/V_offset', 0.6, suffix='V',
               tip='Offset from transistor emitter-follower after low-pass filter.\nPercentage Open = Scale*(V_PWM2 * Gain_LPF - V_offset)')


        # Plot cal
        self.tab_cal.plot = self.tab_cal.add(_g.DataboxPlot(
            autosettings_path = name+'.tab_cal.plot',
            name              = name+'.tab_cal.plot',
            show_logger       = True), alignment=0)


        ######################################
        ## OTHER STUFF

        # Timer for querying arduino state
        self.timer = _g.Timer(250, single_shot=True)
        self.timer.signal_tick.connect(self._timer_tick)
        self.t_connect = None

        # Run stuff after connecting.
        self.serial_gui_base._after_button_connect_toggled = self._after_button_connect_toggled

        self.window.show(block)

    def _number_bias_setpoint_changed(self, *a):
        """
        Update the PWM1 output accordingly, and let its handler do the rest.
        """
        self.number_pwm1_setpoint(self.get_pwm1_from_bias(a[1]))

    def _number_vent_valve_setpoint_changed(self, *a):
        """
        Update the PWM2 output accordingly, and let its handler do the rest.
        """
        self.number_pwm2_setpoint(self.get_pwm2_from_vent_valve_percent(a[1]))

    def _number_bias_limit_changed(self, *a):
        """
        When someone changes the limit, update the bounds.
        """
        # Set the cap. This will adjust the value if needed.
        self.number_bias_setpoint.set_pyqtgraph_options(bounds=(0,a[1]))

        # Set the cap on the other tab.
        self.number_pwm1_limit(self.get_pwm1_from_bias(a[1]))


    def _number_pwm1_limit_changed(self, *a):
        """
        When someone changes the limit, update the bounds on all four.
        """
        # Set the cap. This will adjust the value if needed.
        self.number_pwm1_setpoint.set_pyqtgraph_options(bounds=(0,a[1]))

        # Set the cap on the other tab.
        self.number_bias_limit(self.get_bias_from_pwm1(a[1]))

    def _number_pwm1_setpoint_changed(self, *a):
        """
        Called when someone changes the PWM1 setpoint.
        """
        _debug('_number_pwm1_changed')

        # Send it to the output
        self.set_pwm_voltage_setpoint(1, a[1])

    def _number_pwm2_setpoint_changed(self, *a):
        """
        Called when someone changes the PWM2 setpoint.
        """
        _debug('_number_pwm2_changed')

        # Send it to the output
        self.set_pwm_voltage_setpoint(2, a[1])

    def _button_pump_valve_raw_toggled(self, *a):
        """
        Called when someone toggles the pump valve on the raw tab.
        """
        _debug('_button_pump_valve_raw_toggled')

        # Set the pump valve
        self.set_pump_valve_state(self.button_pump_valve_raw())

    def _button_pump_valve_cal_toggled(self, *a):
        """
        Called when someone toggles the pump valve on the raw tab.
        """
        _debug('_button_pump_valve_cal_toggled')

        # Set the pump valve
        self.set_pump_valve_state(self.button_pump_valve_cal())

    def _button_bias_enabled_toggled(self, value):
        """
        Called when someone toggles the bias button.
        """
        _debug('_button_bias_enabled_toggled', value)

        # Send the command
        self.set_bias_enabled(value)

    def get_adc_voltage(self, n=1):
        """
        Returns the nominal (raw) voltage at Arduino ADC channel n.
        """
        if self.api.simulation_mode: value = _n.random.rand()
        else:                        value = self.api.query('VOLTAGE'+str(int(n))+'?', float)

        # Update the user.
        if value is not None:

            # ADC1 = bias readout
            if   n==1:
                self.number_adc1(value, block_signals=True)
                self.number_bias_measured(self.get_bias_from_adc1(value), block_signals=True)

            # ADC2 = pirani
            elif n==2:
                self.number_adc2(value, block_signals=True)
                self.number_pressure_pirani(self.get_pressure_from_adc2(value), block_signals=True)

            # ADC3 = transducer
            elif n==3:
                self.number_adc3(value, block_signals=True)
                self.number_pressure_transducer(self.get_pressure_from_adc3(value), block_signals=True)

        # None means timeout (as far as I know)
        else: print('get_adc_voltage', n, 'timeout')
        return value

    def get_pwm_voltage_setpoint(self, n):
        """
        Returns the setpoint for PWMn.
        """
        if self.api.simulation_mode: value = _n.random.rand()
        else:                        value = self.api.query('PWM'+str(int(n))+'?', float)

        # Update the user.
        if value is not None:

            # PWM1 = bias setpoint
            if   n==1:
                self.number_pwm1_setpoint(value, block_signals=True)
                self.number_bias_setpoint(self.get_bias_from_pwm1(value), block_signals=True)

            # PWM2 = vent valve setpoint
            elif n==2:
                self.number_pwm2_setpoint(value, block_signals=True)
                self.number_vent_valve_setpoint(self.get_vent_valve_percent_from_pwm2(value), block_signals=True)

        else: print('get_pwm_voltage_setpoint', n, 'timeout')
        return value

    def set_pwm_voltage_setpoint(self, n, V_PWM):
        """
        Sets the target output voltage for PWMn to the value V_PWM (0-3.3V).
        """
        if not self.api.simulation_mode:
            self.api.write('PWM'+str(int(n))+' '+str(V_PWM))

        return self

    def get_pwm1_enabled(self):
        """
        Returns whether the bias is enabled.
        """
        if self.api.simulation_mode: value = _n.random.randint(0,2)
        else:                        value = self.api.query('BIAS:ONOFF?', int)

        if value is not None:
            if value:
                self.button_pwm1_enabled(True, block_signals=True).set_text('Enabled').set_colors('white','red')
                self.button_bias_enabled(True, block_signals=True).set_text('Enabled').set_colors('white','red')
            else:
                self.button_pwm1_enabled(False, block_signals=True).set_text('Disabled').set_colors('white','blue')
                self.button_bias_enabled(False, block_signals=True).set_text('Disabled').set_colors('white','blue')
        return value

    get_bias_enabled = get_pwm1_enabled

    def set_pwm1_enabled(self, enabled=False):
        """
        Enables the bias output if True.
        """
        if not self.api.simulation_mode:
            self.api.write('BIAS:ON' if enabled else 'BIAS:OFF')

        return self

    set_bias_enabled = set_pwm1_enabled

    def get_pump_valve_state(self):
        """
        Returns the status of the relay to the pump valve, with 1 meaning
        "on/open" and 0 meaning "off/closed". Also updates the state in the GUI.
        """
        if self.api.simulation_mode: value = _n.random.randint(0,2)
        else:                        value = self.api.query('RELAY?', int)

        # Update the GUI
        if value is not None:
            if value:
                self.button_pump_valve_raw(True, block_signals=True).set_text('Opened').set_colors('white','red')
                self.button_pump_valve_cal(True, block_signals=True).set_text('Opened').set_colors('white','red')
            else:
                self.button_pump_valve_raw(False, block_signals=True).set_text('Closed').set_colors('white','blue')
                self.button_pump_valve_cal(False, block_signals=True).set_text('Closed').set_colors('white','blue')

        return value

    def set_pump_valve_state(self, state=False):
        """
        Sets the state of the pump valve to open if state is True or 1, and closed
        if False or 0.
        """
        if not self.api.simulation_mode:
            self.api.write('RELAY '+('1' if state else '0'))

        return self

    def _after_button_connect_toggled(self, *a):
        """
        Called after the connect button is toggled.
        """
        # Shortcut.
        self.api = self.serial_gui_base.api

        # If connected
        if self.button_connect():

            # if we have an invalid idn it failed to connect
            if self.api.idn is None and not self.api.simulation_mode:
                self.button_connect(False)
                self.label_message('ERROR: Could not connect to device. Could be in use, the wrong device, or the wrong baud rate.')
                return

            # Update the status label
            if self.api.idn is not None: self.label_status(self.api.idn)
            self.label_message('')

            self.timer.start()
            if self.t_connect is None: self.t_connect = _time.time()


        # Disconnected
        else:
            self.timer.stop()

    def _settings_cal_changed(self, *a):
        """
        Called when one of the cal settings changes.
        """
        print(a)

    def get_bias_from_adc1(self, V_ADC1):
        """
        Given the voltage V_ADC1 from ADC1, returns the actual bias voltage applied
        to the detection circuit (above the big resistor), using the conversion
        parameters in self.conversion.

        Specifically, V_bias = (V_bias:V_ADC1) * V_PWM1
        """
        return self.conversion['Bias/V_bias:V_ADC1']*V_ADC1

    def get_bias_from_pwm1(self, V_PWM1):
        """
        Given the PWM1 setpoint V_PWM1, returns the expected voltage applied
        to the detection circuit (above the big resistor), using the conversion
        parameters in self.conversion.

        Specifically, V_bias = (V_bias:V_PWM1) * V_PWM1
        """
        return self.conversion['Bias/V_bias:V_PWM1']*V_PWM1

    def get_pwm1_from_bias(self, V_bias):
        """
        Given the bias voltage V_bias, returns the corresponding PWM1 setpoint
        voltage (0-3.3V) using the parameters in self.conversion.

        Specifically, V_PWM1 = V_bias / (V_bias:V_PWM1)
        """
        return V_bias / self.conversion['Bias/V_bias:V_PWM1']

    def get_vent_valve_percent_from_pwm2(self, V_PWM2):
        """
        Given the PWM2 setpoint, returns the expected valve position (0-100%)
        from the conversion parameters in self.conversion.

        Specifically Percentage = Scale*(V_PWM2 * Gain_LPF - V_offset)
        """
        Scale    = self.conversion['Vent_Valve/Scale']
        Gain_LPF = self.conversion['Vent_Valve/Gain_LPF']
        V_offset = self.conversion['Vent_Valve/V_offset']
        return Scale*(V_PWM2 * Gain_LPF - V_offset)

    def get_pwm2_from_vent_valve_percent(self, percentage):
        """
        Given the desired vent valve open percentage, returns the corresponding
        PWM2 setpoint (0-3.3V), using the parameters in self.conversion.

        Specifically, V_PWM2 = (V_offset + percentage/Scale) / Gain_LPF
        """
        Scale    = self.conversion['Vent_Valve/Scale']
        Gain_LPF = self.conversion['Vent_Valve/Gain_LPF']
        V_offset = self.conversion['Vent_Valve/V_offset']
        return (V_offset + percentage/Scale) / Gain_LPF

    def get_pressure_from_adc2(self, V_adc2):
        """
        Pirani Guage

        Given the voltage V_adc2 from ADC2, returns the pressure (Pa) estimated
        from the conversion parameters in self.conversion.

        Specifically, P = P_offset + P_scale * 10**((V_adc2-V_offset)/V_scale)
        """
        P_offset = self.conversion['Pirani/P_offset']
        P_scale = self.conversion['Pirani/P_scale']
        V_offset = self.conversion['Pirani/V_offset']
        V_scale = self.conversion['Pirani/V_scale']

        return P_offset + P_scale * 10**((V_adc2-V_offset)/V_scale)

    def get_pressure_from_adc3(self, V_adc3):
        """
        Pressure Transducer

        Given the voltage V_adc3 from ADC3, returns the pressure (Pa) estimated
        from the conversion parameters in self.conversion.

        Specifically, P = P_offset + Ratio*V_adc3
        """
        P_offset = self.conversion['Pressure_Transducer/P_offset']
        Ratio    = self.conversion['Pressure_Transducer/Ratio']

        return P_offset + Ratio * V_adc3

    def _timer_tick(self, *a):
        """
        Called when the update timer ticks.
        """
        self.api.log = None

        # Bias measurement
        V1 = self.get_adc_voltage(1)
        if V1 is None: return
        self.window.process_events()

        # Pirani
        V2 = self.get_adc_voltage(2)
        if V2 is None: return
        self.window.process_events()

        # Pressure transducer
        V3 = self.get_adc_voltage(3)
        if V3 is None: return
        self.window.process_events()

        # Pump valve state (0 or 1)
        pump_valve_open = self.get_pump_valve_state()
        if pump_valve_open is None: return
        self.window.process_events()

        # Bias enabled
        pwm1_enabled = self.get_pwm1_enabled()
        if pwm1_enabled is None: return
        self.window.process_events()

        # Bias setpoint
        pwm1 = self.get_pwm_voltage_setpoint(1)
        if pwm1 is None: return
        self.window.process_events()

        # Vent valve setpoint
        pwm2 = self.get_pwm_voltage_setpoint(2)
        if pwm2 is None: return
        self.window.process_events()

        # Add header information
        self.conversion.send_to_databox_header(self.tab_raw.plot)
        self.conversion.send_to_databox_header(self.tab_cal.plot)

        # Log the raw values.
        self.tab_raw.plot.append_log(

            [_time.time()-self.t_connect,
             V1, V2, V3,
             pwm1_enabled, pwm1, pwm2, pump_valve_open],

            ['t',
             'V1', 'V2', 'V3',
             'PWM1_enabled', 'PWM1', 'PWM2', 'Pump_Valve']

        ).plot()

        # Log the calibrated values
        self.tab_cal.plot.append_log(

            [_time.time()-self.t_connect,

              self.get_bias_from_adc1    (V1),
              self.get_pressure_from_adc2(V2),
              self.get_pressure_from_adc3(V3),

              pwm1_enabled,
              self.get_bias_from_pwm1(pwm1),
              self.get_vent_valve_percent_from_pwm2(pwm2),

              pump_valve_open
              ],

            ['t', 'V_bias_measured(V)', 'Pirani(Pa)', 'Transducer(Pa)',
             'bias_enabled', 'V_bias_setpoint(V)', 'Vent_Valve(%)', 'Pump_Valve' ]

            # ['t', 'V_bias(V)', 'Pirani(Pa)', 'Transducer(Pa)',
            #  'PWM1_enabled', 'V_bias(V)', 'Vent_Valve']

        ).plot()

        self.api.log = print

        self.timer.start()

if __name__ == '__main__':
    _egg.clear_egg_settings()
    self = alpha_arduino()
    #self.button_connect(True)