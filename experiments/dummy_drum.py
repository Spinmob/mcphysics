# Dummy Control code for testing the raw calls.

import serial
import threading
import queue
import numpy
import time

class Vibrating_Plate:
    D_NONE = 0
    D_INFO = 1
    D_OPEN = 2
    D_ALL = 3

    def __init__(self,debug=D_ALL):
        self.handle = False
        self.debug = debug
        self.angulardt = 0.1
        self.radialdt = 0.1

    # Sets the pulse time for the angular motor
    def _angular_set(self,dt):
        self.angulardt = dt

    # Sets the pulse time for the radial motor
    def _radial_set(self,dt):
        self.radialdt = dt

    # Sends the angular motor the given number of steps.
    def _angular_go(self,steps):
        while abs(steps) != 0:
            print("Angular Moving: %d" % steps, end="\r")
            steps = steps - numpy.copysign(numpy.min([50,abs(steps)]),steps)
            time.sleep(self.angulardt)
        print("Angular Move: 0                    ")

    # Sends the radial motor the given number of steps.
    def _radial_go(self,steps):
        while abs(steps) != 0:
            print("Radial Moving: %d" % steps, end="\r")
            steps = steps - numpy.copysign(numpy.min([50,abs(steps)]),steps)
            time.sleep(self.radialdt)
        print("Radial Move: 0                     ")

    # Returns true if the angular motor is not moving
    def _angular_idle(self):
        return True

    # Returns true if the radial motor is not moving
    def _radial_idle(self):
        return True

    # Sends both motors a given number of steps and waits until they're both
    # done moving
    def _go_and_wait(self,angular,radial):
        while not (self.angular_idle() and self.radial_idle()): True
        if (angular != 0): self.angular_go(angular)
        if (radial != 0): self.radial_go(radial)
        while not (self.angular_idle() and self.radial_idle()): True
        return True

    # Added by Rigel:
    def _debug_print(self, message):
        if self.debug:
            print(message)

    def _angular_home(self):
        time.sleep(0.1)
        return True

    def _radial_home(self):
        time.sleep(0.1)
        return True