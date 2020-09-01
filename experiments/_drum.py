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

### Constants
_ANG_MAX_STEPS = 720 # Number of steps that make a full circle
_ANG_MIN_STEPS = 0   # Initial steps in case we want a specific physical angle to be 0 in the future.
_RAD_MAX_STEPS = 10000 # Number of steps from the center to corner of plate

# Since we're on a square. If the sensor is all the way in a corner, rotating
# may result in a collision, so we need to be aware of these bounds.
# TODO: Make sure this number is okay with the installed circular metal drum, or have
#       the class specify the max radius upon creation, with a low default value?
# TODO: Double check if the homing definition of "zero" guaranteed to be sufficiently aligned
#       with the edges of the square plate that it will not collide near the corners?
# TODO: I commented out most of the movement functions, opting for absolute coordinates
#       only. Students can keep track of their coordinates or use the get_ and set_
#       functions, and this will avoid them shifting too far. It also reduces the 
#       immediate work to be done. I've also adopted
#       "r,a" for polar to shorten names, and "_steps" to make as clear as possible
#       when we're talking about steps or absolute (especially brutal with angles!)
#       Please check my factors of 2 and calculations are right, and fill in the
#       calibrations (at least roughly) (search for TODO in this document)
# TODO: (Optional) What if instead of checking and failing, we just have the radial motor
#       drive to the maximum value and print a warning, since all these functions now 
#       return the "actual" value. I'm not wed to this idea, since perhaps the 
#       students should not take such data. Anyway, your call.

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




####################
# Helper Functions #
####################




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
                
                # It all worked, no simulation needed
                self.simulation_mode = False
                
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
    def _angular_home(self):
        if self.simulation_mode: 
            _time.sleep(0.5)
            return True
        
        self._handle.write(b"a_home\n")
        self._wait_for(b"a_home")
        resp = self._wait_for(b"HOMING").decode('ascii')
        print(resp)
        if "FAILED." in resp.split(" "):
            return False
        return True

    # Home the radial motor
    def _radial_home(self):
        if self.simulation_mode: 
            _time.sleep(0.5)
            return True
        
        self._handle.write(b"r_home\n")
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
class motors():
    def __init__(self, port='COM5', debug=True, shape="circle"):
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
        
        To initialize, simply define a new drum object:
        ```
        import safe_drum as sd
        drum = sd.motors()
        ```
        
        This will print out some connection messages, and assuming the device connects
        properly, will home the instrument. If any errors occur during homing, a large
        warning will be displayed, please watch-out for that.
        
        Once homed, you have control of the instrument.  The main moving function is
        `drum.set_ra_steps(r_steps, a_steps)` which sets the scanner to an 
        absolute position defined by a radius and angle.

        Both numbers should be in number of steps for the motor with rough conversion:
        1 Radial step ~ 0.01 mm
        1 Angular step ~ 0.5 degrees of rotaton.

        There are a bunch of wrappers to this motion function, allowing for relative 
        motion and cartesian coordinates. See those functions for more info.


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
    def get_squine_max_steps(self, a_steps):
        """
        Calculates the absolute maximum radius for a given a_steps (in steps) position.
        This is effectively the distance between the center of a square and it's perimiter
        at a given angle. 
        As a multiple of half the square's width, for an edge it's exactly 1, 
        for the exact corner it's sqrt(2). 
        Since the sensor is not a zero-size point, it's width must also be considered.
        This is handled by a multiplicative factor of (0.91 + 0.09 * _n.cos(2*theta)**2), which
        reduces the calculated squine value by a factor of 0.91 at the corner to 1.0 at the edge.
    
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

    def get_squine_max(self, a):
        """
        Returns the maximum allowed radius (follows a squine) for the square plate in mm.
        
        Parameters
        ----------
        a : float
            The angle (degrees).
        
        Returns
        -------
        r_max : float
            Maximum allowed radius (mm).
        """
        r_steps = self.get_squine_max_steps(a*2)
        # TODO: return calibrated radius

    def get_ra_steps(self, *args):
        """
        Returns the current polar coordinates in units of steps.
        
        If the number of arguments is 2, this function will assume they are
        x_steps and y_steps, and calculate r_steps and a_steps from this.
        """
        if len(args) >= 2: 
            
            # Convert to r, a
            x_steps, y_steps = args[0], args[1]
            r_steps = int(_n.round(_n.sqrt(x_steps**2 + y_steps**2)))
            a_steps = int(_n.round(_n.degrees(_n.arctan2(y_steps,x_steps))*2))
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
        
        else: 
            r_steps, a_steps = self._unsafe._radius_steps, self._unsafe._angle_steps    
            x, y = 0, 0 # TODO: insert spec'd calibration
            
        return _n.sqrt(x*x+y*y), _n.degrees(_n.arctan2(y,x))

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
        if len(args) >= 2: r_steps, a_steps = args[0], args[1] 
        else:              r_steps, a_steps = self.get_polar()
        return r_steps*_n.cos(a_steps/2), r_steps*_n.sin(a_steps/2)

    def get_xy(self, *args):
        """
        Returns the current cartesian coordinates x (mm) and y (mm) based on
        the motor and threading specs.
        
        If you specify two arguments, this function will assume they are 
        r (mm) and a (degrees), and use these instead of the internally 
        stored values to calculate the cartesian coordinates.
        """
        if len(args) >= 2: r, a = args[0], args[1]
        else:              r, a = 0, self._unsafe._angle_steps*2 # TODO: insert radial calibration to mm

        return r*_n.cos(a), r*_n.sin(a)

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
            self._unsafe._radius_steps = _RAD_MIN_STEPS
            self._unsafe._angle_steps  = _ANG_MIN_STEPS
            print("Homing Completed Succesfuly.")

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
        a_steps  = int(_n.round(a_steps))
        if not self.is_safe_polar(r_steps, a_steps/2):
            if self._unsafe._shape == "square":
                raise ValueError("Radial position %d outside safe range %d for angular steps %d" % 
                                 (r_steps, self.get_squine_max_steps(a_steps), a_steps))
            if self._unsafe._shape == "circle":
                raise ValueError("Radial position %d outside safe range %d" %
                                 (r_steps, _RAD_MAX_SAFE))

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
            safe_dists = self.get_squine_max_steps(_n.linspace(
                self._unsafe._angle_steps,a_steps,
                _n.abs(self._unsafe._angle_steps-a_steps)+1,
                dtype=int))
            
            safe_dist = _n.min(safe_dists)
            if (ang_delta != 0 and self._unsafe._radius_steps > safe_dist):
                retreat = True
            
            # If we're moving outside the safe radial distance, we want to rotate first.
            if (r_steps > _RAD_MAX_SAFE):
                ang_first = True

            # If we're past the safe rotating radius, pull the radius in.
            if retreat:
                self._unsafe._debug_print("  Retreating radius for rotation by %d steps" % ang_delta)
                # If the target radius is within the safe limit, go there
                # otherwise, move to the minimum safe distance.
                self.set_radius(safe_dist)
        
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

    def set_ra(self, r_target, a_target):
        """
        Sets the radius and angle of the sensor head using the motor and 
        threading specifications. Note the stepper motors will lead to roundoff
        error. Returns the "actual" values based on motor steps and the same specs.
        
        Returns the actual values after rounding to the motor resolution.
        
        Parameters
        ----------
        r_target, a_target : float
            Desired radius (mm) and angle (degrees).   
        
        Returns
        -------
        r, a : (float, float)
            Actual values after rounding to the nearest step.
        """
        # TODO: insert calibration parameters, call set_ra_steps()
        
        # 
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
        #     TODO: Maybe a better approach is to leave x_steps and y_steps as floating point, then
        #           round the radial and angular motor steps at the very end. No reason to enforce
        #           integer x and y. 

        self._unsafe._debug_print('set_xy_steps(%d, %d)' % (x_steps, y_steps))
        
        # Ensure integers, or integer like numbers are passed
        x = int(x_steps)
        y = int(y_steps)
        
        # Assert values are within range
        if not self.is_safe_cartesian(x,y):
            if self._unsafe._shape == "square":
                raise ValueError("Position (%d, %d) contains value outside safe range of %d-%d." % 
                                (x,y, -_RAD_MAX_SAFE, _RAD_MAX_SAFE))
                raise ValueError("Position (%d, %d) produces radius %d outside limit of %d." % 
                                (x,y, int(round(_n.sqrt(x**2+y**2))), _RAD_MAX_SAFE))

        # Convert x,y to r,theta
        r     = _n.sqrt(x**2 + y**2)
        theta = _n.degrees(_n.arctan2(y,x))
    
        # Convert to steps
        # This will probably introduce some rounding error...
        radial = int(round(r))
        angular = int(round(theta * 2))

        self.set_ra_steps(radial, angular)
        
        # Return the actual values.
        return self.get_xy_steps()

    def set_xy(self, x_target, y_target):
        """
        Sets the cartesian coordinates of the sensor head using the motor and 
        threading specifications. Note the stepper motors will lead to roundoff
        error. Returns the "actual" values based on the same specs.
        
        Returns the actual values after rounding to the motor resolution.
        
        Parameters
        ----------
        x_target, y_target : float
            Desired x and y positions (mm).  
        
        Returns
        -------
        x, y : (float, float)
            Actual values after rounding to the nearest step.
        """
        # TODO: insert calibration parameters, call set_ra_steps(), return self.get_ra()
        

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
    #     a = self._unsafe._angle_steps/2 # TODO: This is the motor's calibration? 
    #     x_cur = r * _n.cos(a)
    #     y_cur = r * _n.sin(a)
        
    #     # This will probably introduce some rounding error...
    #     x_cur = int(round(x_cur))
    #     y_cur = int(round(y_cur))

    #     # Compute new absolute cartesian coordinates
    #     new_x = x_steps + x_cur
    #     new_y = y_steps + y_cur

    #     self.set_xy_steps(new_x, new_y)

    def is_safe_polar(self, r_steps, a_steps):
        """ 
        Returns true if the given polar coordinates are safe for the vibrating plate.
        Tip: You can use this to filter a list of coordinates to ensure that no errors occur
            while scanning through them.

        Parameters
        ----------
        r : int or float
            The radius of the given position. To be safe, this value must be within
            the minimal safe radius, and the maximum safe radius for the given angle.
        theta : int or float
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
            return not (r_steps < _RAD_MIN_STEPS or r_steps > self.get_squine_max_steps(a_steps))
        elif self._unsafe._shape == "circle":
            return not (r_steps < _RAD_MIN_STEPS)

    def is_safe_cartesian(self, x_steps, y_steps):
        """ Returns true if the given cartesian coordinates are safe for the vibrating drum.
            Tip: You can use this to filter a list of coordinates to ensure that no errors occur
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
            checks = [(pos < -_RAD_MAX_SAFE or pos > _RAD_MAX_SAFE) for pos in [x_steps,y_steps]]
            return not any(checks)
        if self._unsafe._shape == "circle":
            r = _n.sqrt(x_steps**2 + y_steps**2)
            return r <= _RAD_MAX_SAFE

# Testing will remove
if __name__ == "__main__":
    
    plate = motors('COM5')
    
    # Test Polar Bounds
    for i in range(0,360,60):
        print('\nangle', i)
        plate.set_ra_steps(plate.get_squine_max_steps(i),i)
    
    # Test Cartesian Bounds
    for i in range(-7000,7200,200):
        print('\nposition', i)
        plate.set_xy_steps(i,i)
        
    plate.set_ra_steps(0,0)

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