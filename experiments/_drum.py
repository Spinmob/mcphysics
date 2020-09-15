# Safe control code written by Rigel Zifkin 2020-08-09
# Tweaked by Jack Sankey, 2020.08

# Original code by Mark Orchard-Webb,
# Tweaked by:
#            Robert Turner, 2019.12.09
#            Rigel Zifkin, 2020.08.09
#            Jack Sankey, 2020.08

# By convention, any time both sensor coordinates are specified simultaneously,
# the order should be radial, angular for polar coordinates
# and x,y for cartesian coordinates

# Since we're on a square. If the sensor is all the way in a corner, rotating
# may result in a collision, so we need to be aware of these bounds.

# TODO: get_squine_max_steps() and get_squine_max() should be replaced with
#       get_max_r_steps() and get_max_r(), with a check against the shape to
#       determine whether a squine or simple limit is required. Not a big priority
#       before term start, since students only really need get_xy() and set_xy().

### Constants
_ANG_MAX_STEPS = 720 # Number of steps that make a full circle
_ANG_MIN_STEPS = 0   # Initial steps in case we want a specific physical angle to be 0 in the future.
_ANG_STEPS_PER_DEG = 2

_RAD_STEPS_PER_MM = 28*100/25.4 # Rod is 28 TPI, 100 steps per motor rotation, 25.4 mm/in
_RAD_MAX_STEPS = 10000 # Number of steps from the center to corner of plate
_RAD_MAX_SAFE  = 7300 # Number of steps from center to edge of plate
_RAD_MIN_STEPS = 0 # Initial steps in case we want a specific radius to be 0.

# Aliases
import mcphysics as _mp
adalm2000  = _mp.instruments.adalm2000
sillyscope = _mp.instruments.sillyscope
soundcard  = _mp.instruments.soundcard

import serial    as _serial
import threading as _threading
import queue     as _queue
import numpy     as _n
import time      as _time

get_com_ports  = _mp.instruments._serial_tools.get_com_ports
list_com_ports = _mp.instruments._serial_tools.list_com_ports


class _unsafe_motors:
    """
    Class for talking to the motors. Pays no mind to whether it will crash into
    walls.

    Parameters
    ----------
    port='COM5' : str or None
        Port to assume is the controlling arduino.
        Setting to None or "Simulation" means simulation mode.
    """


    D_NONE = 0
    D_INFO = 1
    D_OPEN = 2
    D_ALL = 3

    def __init__(self, port='COM5', debug=D_ALL):
        self._handle = False
        self.debug = debug

        if port in [None, "Simulation"]:
            self.simulation_mode = True

        # Otherwise give it a shot.
        else:
            # Attempt to open the com port.
            try:
                # Hopeful it all all works, no simulation needed
                self.simulation_mode = False

                device = port
                if self.D_OPEN & self.debug: print("Attempting '%s'"%(device))
                self._handle = _serial.Serial(device,115200) # 115200 = Data Rate

                # Open queue for threaded communication with device.
                self._queue = _queue.Queue()
                t = _threading.Thread(target=self._reader)
                t.daemon = True
                t.start()
                self._debug_print("thread started")
                while False == self._timeout_for(b"reset",timeout=1):
                    self._debug_print("resetting")
                    self._handle.write(b"reset\n")

            # Whoopsie-doodle
            except Exception as e:
                print("Exception:", e, 'entering simulation mode...')
                self.simulation_mode = True


    def _reader(self):
        if self.simulation_mode:
            _time.sleep(0.5)
            return

        self._debug_print("reader starts")
        while True:
            str = self._handle.readline()
            self._queue.put(str)

    # Wait for message matching "str", with max wait time "timeout"
    def _timeout_for(self,str,timeout):
        if self.simulation_mode:
            _time.sleep(0.5)
            return 'fake response from _timeout_for'

        while True:
            try:
                resp = self._queue.get(block=True,timeout=timeout)
                self._debug_print("after get")
                self._queue.task_done()
                rc = resp.find(str)
                if 0 == rc : return resp
                print("UnMatched: %s" % (resp.decode()))
            except _queue.Empty:
                self._debug_print("exception")
                return False

    # Wait for message matching "str" with no max time
    def _wait_for(self,str,timeout=None):
        if self.simulation_mode:
            _time.sleep(0.5)
            return 'fake response from _wait_for'

        while True:
            resp = self._queue.get()
            self._queue.task_done()
            if 0:
                print((b"wait_for() read: "),)
                print((resp),)
            if "ERR:" == resp[0:4]:
                print(resp)
                raise RuntimeError
            rc = resp.find(str)
            if 0 == rc : return resp
            print(b"Unmatched: %s" % (resp),)

    # Set debug mode? Not really sure yet.
    def _debug(self):
        if self.simulation_mode:
            _time.sleep(0.5)
            return

        self._handle.write(b"debug\n");
        self._wait_for(b"debug")
        return;

    # Get the device status
    def _status(self):
        if self.simulation_mode:
            _time.sleep(0.5)
            return

        self._handle.write(b"status\n");
        self._wait_for(b"status")
        return;

    # Sets the pulse time for the angular motor
    def _angular_set(self,dt):
        if self.simulation_mode:
            _time.sleep(0.5)
            return _n.random.rand()

        command = b"a_set %f\n" % (dt)
        self._handle.write(command);
        resp = self._wait_for(b"a_set")
        words = resp.split(b" ")
        return int(words[1])/48e3 # samples/samplerate

    # Sets the pulse time for the radial motor
    def _radial_set(self,dt):
        if self.simulation_mode:
            _time.sleep(0.5)
            return _n.random.rand()

        command = b"r_set %f\n" % (dt)
        self._handle.write(command);
        resp = self._wait_for(b"r_set")
        words = resp.split(b" ")
        return int(words[1])/48e3 # samples/samplerate

    # Sends the angular motor the given number of steps.
    def _angular_go(self,steps):
        if self.simulation_mode:
            _time.sleep(0.5)
            return True

        command = b"a_go %d\n" % (steps)
        self._handle.write(command);
        self._wait_for(b"a_go")
        return True

    # Sends the radial motor the given number of steps.
    def _radial_go(self,steps):
        if self.simulation_mode:
            _time.sleep(0.5)
            return True

        command = b"r_go %d\n" % (steps)
        self._handle.write(command);
        self._wait_for(b"r_go")
        return True

    # Returns true if the angular motor is not moving
    def _angular_idle(self):
        if self.simulation_mode:
            _time.sleep(0.5)
            return True

        self._handle.write(b"a_idle\n")
        resp = self._wait_for(b"a_idle")
        return b"true" == resp[7:11]

    # Returns true if the radial motor is not moving
    def _radial_idle(self):
        if self.simulation_mode:
            _time.sleep(0.5)
            return True

        self._handle.write(b"r_idle\n")
        resp = self._wait_for(b"r_idle")
        return b"true" == resp[7:11]

    # Home the angular motor
    def _angular_home(self, max_steps=_ANG_MAX_STEPS):
        if self.simulation_mode:
            _time.sleep(0.5)
            return True

        self._handle.write(b"a_home %d\n" % int(max_steps))
        self._wait_for(b"a_home")
        resp = self._wait_for(b"HOMING").decode('ascii')
        if "FAILED." in resp.split(" "):
            return False
        return True

    # Home the radial motor
    def _radial_home(self, max_steps=_RAD_MAX_SAFE):
        if self.simulation_mode:
            _time.sleep(0.5)
            return True

        self._handle.write(b"r_home %d\n" % int(max_steps))
        self._wait_for(b"r_home")
        resp = self._wait_for(b"HOMING").decode('ascii')
        if "FAILED." in resp.split(" "):
            return False
        return True

    # Sends both motors a given number of steps and waits until they're both
    # done moving
    def _go_and_wait(self,angular,radial):
        if self.simulation_mode:
            _time.sleep(0.5)
            return True

        while not (self._angular_idle() and self._radial_idle()): True
        if (angular != 0): self._angular_go(angular)
        if (radial != 0): self._radial_go(radial)
        while not (self._angular_idle() and self._radial_idle()): True
        return True

    # Added by Rigel:
    def _debug_print(self, message):
        if self.debug:
            print(message)




######################################
# Safe Motor Control Class           #
######################################
class motors_api():
    """
    A safe wrapper for controlling the drum stepper motors lab.
    Everytime an instance is opened, the experiment is homed, this uses
    limit switches to set the apparatus to its (0,0) position.

    Moving the equpiment is then done using "safe" functions.

    WARNING: You should have no reason to access and functions/fields prefixed
             with an underscore '_'. Python leaves these fully accessible and you can
             100% break the equipment if you mess with them. If you really
             think you need to for some fantastic new functionality that will
             make the experiment go better, please contact a TA/Prof first.

    Prior to creating an instance, make sure you can see the sensor (e.g., via
    a webcam) so you know whether it's actually moving.

    When a new instance is created, it will print out some connection messages,
    and assuming the device connects properly, will home the instrument. If
    any errors occur during homing, a large warning will be displayed, please
    watch-out for that.

    Parameters
    ----------
    port='COM5' : str or None
        Port to assume is the controlling arduino.
        Setting to None or "Simulation" means simulation mode.

    debug : bool, optional
        Whether to print verbose debug messages, by default True

    shape : str, optional
        The shape of the plate in the apparatus. Can be one of
        "circle" or "square", by default circle, for safety.
    """

    def __init__(self, port=None, shape=None, debug=False):

        if port is None:
            print('ERROR: You must specify a port.')
            _mp.experiments.drum.list_com_ports()
            return

        if not shape in ['square', 'circle']:
            raise Exception('"shape" argument must be either "square" or "circle".')

        # Unsafe API
        self._unsafe = _unsafe_motors(port, debug)

        # Home the instrument on every startup, that way we are always at 0,0
        # from the beginning
        self._unsafe._radius_steps = _RAD_MIN_STEPS
        self._unsafe._angle_steps  = _ANG_MIN_STEPS
        self._unsafe._shape = shape
        self.home()

    # For a given angle theta, max radial position is squine(theta)
    # Here's a function for getting that as a function of angular steps
    # Not good enough since the sensor has some width to it.
    # For now gonna try multiplying by (0.91 + 0.09 * cos(2*theta)**2) in order
    # to smoothly go from edge at angle 0 to corner at angle 45.
    def get_squadius_steps(self, a_steps):
        """
        Calculates the absolute maximum radius for a given a_steps (in steps) position.
        This is effectively the distance between the center of a square and it's perimiter
        at a given angle.
        As a multiple of half the square's width, for an edge it's exactly 1,
        for the exact corner it's sqrt(2).
        Since the sensor is not a zero-size point, it's width must also be considered.
        This is handled by a multiplicative factor of (0.91 + 0.09 * _n.cos(2*theta)**2), which
        reduces the calculated squadius value by a factor of 0.91 at the corner to 1.0 at the edge.

        Parameters
        ----------
        a_steps : int
            the a_steps position in steps.

        Returns
        -------
        int
            the maximum position in steps of the radial motor for the sensor to not
            collide with the walls.
        """
        theta = (a_steps/_ANG_MAX_STEPS) * 2 * _n.pi
        multiple = (0.91 + 0.09 * _n.cos(2*theta)**2) * _RAD_MAX_SAFE
        # Don't care about divide by zero within the following math
        with _n.errstate(divide='ignore'):
            return  multiple * _n.min(_n.abs([1/_n.cos(theta), 1/_n.sin(theta)]), axis=0)

    # I don't think we need this given get_max_r() - Rigel
    # def get_squadius_max(self, a):
    #     """
    #     Returns the maximum allowed radius for the square plate in mm.

    #     Parameters
    #     ----------
    #     a : float
    #         The angle (degrees).

    #     Returns
    #     -------
    #     r_max : float
    #         Maximum allowed radius (mm).
    #     """
    #     a_steps = a*_ANG_STEPS_PER_DEG
    #     r_steps = self.get_squine_max_steps(a_steps)
    #     return r_steps / _RAD_STEPS_PER_MM

    def get_max_r_steps(self, a_steps = None):
        """
        Get the maximum allowable radius in steps with the actuator at a given angle in steps.

        Parameters
        ----------
        a_steps : int, optional
            The angle in steps to calculate the max radius at, only relevant for a square plate.
            If not given, will take the current angular position.

        Returns
        -------
        int
            the maxiam radius in steps for the given angle.
        """
        if self._unsafe._shape == "circle":
            return _RAD_MAX_SAFE
        elif self._unsafe._shape == "square":
            if a_steps is None:
                a_steps = self.get_ra_steps()[1]
            return self.get_squadius_steps(a_steps)

    def get_max_r(self, a=None):
        """
        Get the maximum allowable radius in mm with the actuator at a given angle in degrees

        Parameters
        ----------
        a : int, optional
            The angle in degrees to calculate the max radius at, only relevant for a square plate.
            If not given, will take the current angular position.

        Returns
        -------
        int
            the maximum radius in steps for the given angle.
        """

        max_r_steps = self.get_max_r_steps(None if a is None else a * _ANG_STEPS_PER_DEG)
        return max_r_steps / _RAD_STEPS_PER_MM

    def get_ra_steps(self, *args):
        """
        Returns the current polar coordinates in units of steps.

        If the number of arguments is 2, this function will assume they are
        x_steps and y_steps, and calculate r_steps and a_steps from this.
        """
        if len(args) >= 2:

            # Convert to r, a
            x_steps, y_steps = args[0], args[1]
            r_steps = int(_n.round(_n.hypot(x_steps,y_steps)))
            a_steps = int(_n.round(_n.degrees(_n.arctan2(y_steps,x_steps))*_ANG_STEPS_PER_DEG))
            return r_steps, a_steps

        return self._unsafe._radius_steps, self._unsafe._angle_steps

    def get_ra(self, *args):
        """
        Returns the current polar coordinates r (mm) and a (degrees).

        If the number of arguments is 2, this function will assume they are
        x and y, and calculate r and a from this.
        """
        if len(args) >= 2:
            x, y = args[0], args[1]
            return _n.hypot(x,y), _n.degrees(_n.arctan2(y,x))

        else:
            r_steps, a_steps = self.get_ra_steps()
            return r_steps/_RAD_STEPS_PER_MM, a_steps/_ANG_STEPS_PER_DEG

    # def get_radial_steps(self):
    #     """
    #     Returns the current radial motor step count.
    #     """
    #     return self._unsafe._radius_steps

    # def get_angular_steps(self):
    #     """
    #     Returns the current angular motor step count.
    #     """
    #     return self._unsafe._angle_steps

    def get_xy_steps(self, *args):
        """
        Returns the current cartesian coordinates in units of steps.

        If you specify two arguments, this function will assume they are
        r_steps and a_steps, and use these instead of the internally stored
        values to calculate the cartesian coordinates.
        """
        if len(args) >= 2:
            r_steps, a_steps = args[0], args[1]
        else:
            r_steps, a_steps = self.get_ra_steps()

        a = a_steps/_ANG_STEPS_PER_DEG
        return r_steps*_n.cos(_n.radians(a)), r_steps*_n.sin(_n.radians(a))

    def get_xy(self, *args):
        """
        Returns the current cartesian coordinates x (mm) and y (mm) based on
        the motor and threading specs.

        If you specify two arguments, this function will assume they are
        r (mm) and a (degrees), and use these instead of the internally
        stored values to calculate the cartesian coordinates.
        """
        if len(args) >= 2:
            r, a = args[0], args[1]
        else:
            r,a = self.get_ra()

        return r*_n.cos(_n.radians(a)), r*_n.sin(_n.radians(a))

    def home(self):
        """
        Moves the radial and angular motor backwards until they hit the limit switches.
        This defines the minimal position of the scanner along both axes.
        """
        if self.get_ra_steps()[1] > 710:
            self.set_ra_steps(self.get_ra_steps()[0], 710)
        print("Homing Instrument, please wait")

        if self._unsafe.simulation_mode:
            _time.sleep(0.5)
            r_status = True
            a_status = True

        else:
            r_status = self._unsafe._radial_home()
            a_status = self._unsafe._angular_home()

        if not (r_status and a_status):
            if r_status:
                print("Radial Switch Failed.")
            if a_status:
                print("Angular Switch Failed.")
            print("!!!!!!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~!!!!!!")
            print("Homing Failed, please check the camera and contact technician if needed.")
            print("If the radial switch is obviously not engadged, run home() again.")
            print("Otherwise, immediatly get help and do not run any other commands.")
            print("!!!!!!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~!!!!!!")
            input("Press Enter to acknowledge this message...")

        else:
            # ADD A +1 angle bump so it doesn't walk backwards.
            self._unsafe._angular_go(1)

            # Call this "zero"
            self._unsafe._radius_steps = _RAD_MIN_STEPS
            self._unsafe._angle_steps  = _ANG_MIN_STEPS
            print("Homing Completed Succesfully.")



    def set_ra_steps(self, r_steps, a_steps):
        """
        Steps the radial and angular motors to the specified position relative
        to zero.

        Returns the actual values after rounding to the motor resolution (integer steps).

        This method protects the motor and sensor through several precautions:
            * Ensures limits are established on the given positions.
            * Automatically adjusts angular steps so that the actuator never performs
              more than a full rotation.
            * Calculates the max sensor radius for a given angle, and ensures
              the sensor does not collide with the walls of the square plate while moving
              to this position.

        Parameters
        ----------
        r_steps : float
            The position, in steps, relative to zero to move the radial position to.

        a_steps : float
            The position, in steps, relative to zero to move the angular position to.
            Currently, each a_step is 1/2 of a degree.

        Returns
        -------
        r_steps, a_steps : int
            Values the motors were set to (steps).

        Raises
        ------
        ValueError
            Will return this error if the radius is attempted to be set outside of the max range,
            or if it's set to a radius that is incompatible with the desired angular position.
        """
        self._unsafe._debug_print('set_ra_steps(%d, %d)' % (r_steps, a_steps))

        # Ensure integers, or integer like numbers are passed
        r_steps = int(_n.round(r_steps))
        a_steps = int(_n.round(a_steps))

        # Make sure it's within bounds.
        if not self.is_safe_ra_steps(r_steps, a_steps):
            raise ValueError("Out of bounds: r_steps=%d, a_steps=%d" % (r_steps, a_steps))

        # Take absolute position around single rotation of circle
        ang_delta = (a_steps % _ANG_MAX_STEPS) - self._unsafe._angle_steps
        ang_first = False
        if self._unsafe._shape == "square":

            # Flags that modify how the motion should be handled
            retreat = False
            ang_first = False

            # If the radius is outside the safe range and we're rotating
            # we need to first pull in the sensor, then do the rotation
            # and finally set the radius to the correct amount.

            # Need to consider every angle we pass through and find the lowest
            # possible maximum radius.
            angles = _n.linspace(self._unsafe._angle_steps,a_steps,
                                 _n.abs(self._unsafe._angle_steps-a_steps)+1,
                                 dtype=int)
            safe_dists = self.get_max_r_steps(angles)
            safe_dist = _n.min(safe_dists)

            if (ang_delta != 0 and self._unsafe._radius_steps > safe_dist):
                retreat = True

            # If we're moving outside the safe radial distance, we want to rotate first.
            if (r_steps > _RAD_MAX_SAFE):
                ang_first = True

            # If we're past the safe rotating radius, pull the radius in.
            if retreat:
                self._unsafe._debug_print("Retreating radius for rotation by %d steps" % ang_delta)
                # If the target radius is within the safe limit, go there
                # otherwise, move to the minimum safe distance.
                self.set_ra_steps(safe_dist,self._unsafe._angle_steps)

        # Calculate number of steps needed to move radially.
        # Put here since retreating will change this.
        rad_delta = r_steps - self._unsafe._radius_steps

        self._unsafe._debug_print(
            "  Moving to:      %d, %d" % (self._unsafe._radius_steps + rad_delta,
                                             self._unsafe._angle_steps  + ang_delta))

        # If there is motion to do, send the motors that number of steps
        # and wait until idle.
        if ang_delta != 0:
            self._unsafe._angular_go(ang_delta)
            # If we need the angular motion to finish before the radial motion starts, wait here.
            if ang_first:
                self._unsafe._debug_print("  Rotating Angle First")
                while not self._unsafe._angular_idle():
                    _time.sleep(0.1)

        if rad_delta != 0:
            self._unsafe._radial_go(rad_delta)

        # Wait for all movement to stop.
        while not (self._unsafe._radial_idle() or self._unsafe._angular_idle()):
            _time.sleep(0.1)

        # Register the new changes
        self._unsafe._angle_steps += ang_delta
        self._unsafe._radius_steps += rad_delta
        self._unsafe._debug_print("  Final Position: %d, %d" % (self._unsafe._radius_steps,
                                                                self._unsafe._angle_steps))

        # Return the actual values
        return self.get_ra_steps()

    def set_ra(self, r_mm, a_degrees):
        """
        Sets the radius and angle of the sensor head using the motor and
        threading specifications. Note the stepper motors will lead to roundoff
        error. Returns the "actual" values based on motor steps and the same specs.

        Returns the actual values after rounding to the motor resolution.

        Parameters
        ----------
        r, a : float
            Desired radius (mm) and angle (degrees).

        Returns
        -------
        r, a : (float, float)
            Actual values after rounding to the nearest step.
        """
        r_steps = r_mm      * _RAD_STEPS_PER_MM
        a_steps = a_degrees * _ANG_STEPS_PER_DEG
        self.set_ra_steps(r_steps, a_steps)
        return self.get_ra()

    # def shift_radius(self, steps):
    #     """
    #     Step the radial motor by a given number of steps.
    #     Wrapper for set_ra_steps(), see that documentation for more info.

    #     Parameters
    #     ----------
    #     steps : int
    #         The number of steps to actuate the motor.
    #         Positive number indicates increasing radius.
    #         Negative number indicates decreasing radius.
    #     """
    #     self.shift_polar(steps, 0)

    # def set_radius(self, steps):
    #     """
    #     Steps the radial motor to an absolute position given by 'steps' from zero.
    #     Wrapper for set_ra_steps(), see that documentation for more info.

    #     Parameters
    #     ----------
    #     steps : int
    #         The position in steps, relative to zerodrum to move the radial position to.
    #     """
    #     self.set_ra_steps(steps, self._unsafe._angle_steps)

    # def shift_angle(self, steps):
    #     """
    #     Step the angular motor by a given number of steps.
    #     Wrapper for set_ra_steps(), see that documentation for more info.

    #     Parameters
    #     ----------
    #     steps : int
    #         The number of steps to actuate the motor.
    #         Positive number indicates clockwise motion (looking from above).
    #         Negative number indicates counterclockwise motion (looking from above).
    #     """
    #     self.shift_polar(0, steps)

    # def set_angle(self, steps):
    #     """
    #     Steps the angular motor to an absolute position given by 'steps' from zero.
    #     Wrapper for set_ra_steps(), see that documentation for more info.

    #     Parameters
    #     ----------
    #     steps : int
    #         The position in steps, relative to zero to move the angular position to.
    #     """
    #     self.set_ra_steps(self._unsafe._radius_steps, steps)

    # def shift_polar(self, r_steps, a_steps):
    #     """Step the radial and angular motor by a given number of steps.
    #        Wrapper for set_ra_steps(), see that documentation for more info.

    #     Parameters
    #     ----------
    #     r_steps : int
    #         The number of steps to actuate the radial motor.
    #         Positive number indicates forward motion.
    #         Negative number indicates backwards motion.
    #     a_steps : int
    #         The number of steps to actuate the angular motor.
    #         Positive number indicates clockwise motion (looking from above).
    #         Negative number indicates counterclockwise motion (looking from above).
    #     """
    #     self.set_ra_steps(self._unsafe._radius_steps + r_steps, self._unsafe._angle_steps + a_steps)

    def set_xy_steps(self, x_steps, y_steps):
        """
        Steps the radial and angular motors to a cartesian position (x_steps,y).
        This is done by converting the x_steps and y values to polar coordinates,
        so it may result in slightly different positions due to rounding.

        Returns the actual values after rounding to the motor resolution.

        Parameters
        ----------
        x_steps : int
            The position in steps along the x axis to position the sensor.

        y_steps : int
            The position in steps along the y axis to position the sensor.

        Returns
        -------
        x_steps, y_steps: float, float
            Actual values of x and y in units of steps after rounding to
            the motors' resolution.

        Raises
        ------
        ValueError
            Will return an error if the given coordinates are outisde the range set
            by +/- the maximum safe radius.
        """
        # TODO: Test that non-integer x_step and y_steps are ok.

        self._unsafe._debug_print('set_xy_steps(%f, %f)' % (x_steps, y_steps))

        # Assert values are within range
        if not self.is_safe_xy_steps(x_steps,y_steps):

            # Squarror
            if self._unsafe._shape == "square":
                raise ValueError("Position (%f, %f) contains value outside safe range of %d-%d." %
                                (x_steps, y_steps, -_RAD_MAX_SAFE, _RAD_MAX_SAFE))

            # Circle
            else:
                raise ValueError("Position (%f, %f) produces radius %d outside limit of %d." %
                                (x_steps, y_steps, int(round(_n.hypot(x_steps,y_steps))), _RAD_MAX_SAFE))

        # Convert to steps
        # This will probably introduce some rounding error...
        r_steps, a_steps = self.get_ra_steps(x_steps, y_steps)

        self.set_ra_steps(r_steps, a_steps)

        # Return the actual values.
        return self.get_xy_steps()

    def set_xy(self, x_mm, y_mm):
        """
        Sets the cartesian coordinates of the sensor head using the motor and
        threading specifications. Note the stepper motors will lead to roundoff
        error.

        Returns the actual values after rounding to the motor resolution.

        Parameters
        ----------
        x, y : float
            Desired x and y positions (mm).

        Returns
        -------
        x, y : (float, float)
            Actual values after rounding to the nearest step.
        """
        # Get the non-step radius and angle and set it, and then get the actual
        r, a = self.get_ra(x_mm,y_mm)
        self.set_ra(r, a)
        return self.get_xy()


    # def shift_cartesian(self, x_steps, y_steps):
    #     """
    #     Steps the radial and angular motors to move relative to the current position a number
    #     of steps given (x,y) in cartesian coordinates.
    #     This requires converting the current position to cartesian, calculating the new
    #     position and converting back to polar, and will likely result in a slightly different
    #     position due to rounding.


    #     Parameters
    #     ----------
    #     x_steps : int
    #         The number of steps to move along the x-axis
    #     y_steps : int
    #         The number of steps to move along the y-axis
    #     """
    #     # Get current position in cartesian
    #     r = self._unsafe._radius_steps
    #     a = self._unsafe._angle_steps
    #     x_cur = r * _n.cos(_n.radians(a))
    #     y_cur = r * _n.sin(_n.radians(a))

    #     # This will probably introduce some rounding error...
    #     x_cur = int(round(x_cur))
    #     y_cur = int(round(y_cur))

    #     # Compute new absolute cartesian coordinates
    #     new_x = x_steps + x_cur
    #     new_y = y_steps + y_cur

    #     self.set_xy_steps(new_x, new_y)

    def is_safe_ra_steps(self, r_steps, a_steps):
        """
        Returns true if the given polar coordinates are safe for the vibrating plate.
        Tip: You can use this to filter a list of coordinates to ensure that no errors occur
            while scanning through them.

        Parameters
        ----------
        r_steps : int or float
            The radius of the given position. To be safe, this value must be within
            the minimal safe radius, and the maximum safe radius for the given angle.

        a_steps : int or float
            The angle of the given position. This has no limitations as the angle
            will be automatically wrapped if it exceeds a full turn.

        Returns
        -------
        bool
            Returns true if the position is safe, and false otherwise.
        """
        r_steps = int(round(r_steps))
        a_steps = int(round(a_steps))

        if self._unsafe._shape == "square":
            return not (r_steps < _RAD_MIN_STEPS or r_steps > self.get_max_r_steps(a_steps))
        elif self._unsafe._shape == "circle":
            return not (r_steps < _RAD_MIN_STEPS or r_steps > _RAD_MAX_SAFE)

    def is_safe_ra(self, r, a):
        """
        Returns True if the given radius r (mm) and angle a (degrees) is within
        the bounds of the selected shape.

        Parameters
        ----------
        r, a : float
            Radius r (mm) and angle a (degrees) of the sensor head.

        Returns
        -------
        bool
            True if position is safe, False otherwise.
        """
        r_steps = r * _RAD_STEPS_PER_MM
        a_steps = a * _ANG_STEPS_PER_DEG
        return self.is_safe_ra_steps(r_steps, a_steps)


    def is_safe_xy_steps(self, x_steps, y_steps):
        """
        Returns true if the given cartesian coordinates are safe for the vibrating drum.
        Pro Tip: You can use this to filter a list of coordinates to ensure that no errors occur
                 while scanning through them.

        Parameters
        ----------
        x_steps : int or float
            The x coordinate of the given position. To be safe this value must be
            within +/- the maximum safe radius
        y_steps : int or float
            The y coordinate of the given position. To be safe this value must be
            within +/- the maximum safe radius

        Returns
        -------
        bool
            Returns true if the position is safe, and false otherwise.
        """
        if self._unsafe._shape == "square":
            checks = [(p < -_RAD_MAX_SAFE or p > _RAD_MAX_SAFE) for p in [x_steps,y_steps]]
            return not any(checks)
        if self._unsafe._shape == "circle":
            r = _n.hypot(x_steps, y_steps)
            return r <= _RAD_MAX_SAFE

    def is_safe_xy(self, x, y):
        """
        Returns True if the given x (mm) and y (mm) are within
        the bounds of the selected shape.

        Parameters
        ----------
        x, y : float
            Cartesian coordinates (mm) of the sensor head.

        Returns
        -------
        bool
            True if position is safe, False otherwise.
        """
        x_steps = _RAD_STEPS_PER_MM * x
        y_steps = _RAD_STEPS_PER_MM * y
        return self.is_safe_xy_steps(x_steps,y_steps)

# Testing will remove
if __name__ == "__main__":

    # plate = motors_api('COM5')

    # # Test Polar Bounds
    # for i in range(0,360,60):
    #     print('\nangle', i)
    #     plate.set_ra_steps(plate.get_squine_max_steps(i),i)

    # # Test Cartesian Bounds
    # for i in range(-7000,7200,200):
    #     print('\nposition', i)
    #     plate.set_xy_steps(i,i)

    # plate.set_ra_steps(0,0)

    # Test is_safe
    self = motors_api('COM5', shape='circle')
    import pylab

    pylab.figure(1)
    pylab.ioff()
    N = 100
    for x in _n.linspace(-N, N, 50):
        for y in _n.linspace(-N, N, 50):
            if self.is_safe_xy(x,y):
                pylab.plot([x],[y], marker='o', ls='')
    pylab.ion()
    pylab.show()

    pylab.figure(2)
    pylab.ioff()
    N = 100
    for r in _n.linspace(0, N, 20):
        for a in _n.linspace(-360, 360, 50):
            if self.is_safe_ra(r,a):
                pylab.plot([r*_n.cos(_n.radians(a))],
                           [r*_n.sin(_n.radians(a))], marker='o', ls='')
    pylab.ion()
    pylab.show()


"""

    # Set position to 0, 0
    #drum.home()
    # Testing basic moves
    drum.set_ra_steps(100,100)
    drum.set_ra_steps(200,200)
    drum.set_ra_steps(100,100)

    # Testing Bounds
    drum.set_ra_steps(100,820)
    drum.set_ra_steps(100,-820)
    try:
        drum.set_ra_steps(100000, 90)
    except ValueError:
        print("Caught Exception - Radius way to big")
        pass

    # Testing Safe Rotation
    drum.radial_set(0.01)
    drum.set_ra_steps(11000, 90)
    try:
        drum.set_ra_steps(10050, 360)
    except ValueError:
        print("Caught Exception - Radius outside safe range")

    drum.set_ra_steps(300,0)
    drum.radial_set(0.1)
"""