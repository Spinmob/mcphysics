import mcphysics as _mp; libm2k = _mp._m2k

# import libm2k
import pylab
import numpy

# Get the first m2k name
name = libm2k.getAllContexts()[0]

# Get the m2k
m2k = libm2k.m2kOpen(name).toM2k()

# Run the calibration
m2k.calibrate()

# Enable the first output, enable it, and send it some data.
ao = m2k.getAnalogOut()
ao.enableChannel(0, True)
ao.enableChannel(1, True)
ao.setSampleRate(0, 75000000)
ao.setSampleRate(1, 75000000)

# Waveforms: sinusoid and square pulse
N  = 100                        # Number of samples to stream
ns = numpy.linspace(0,N-1,N)    # List of integers
v1 = numpy.sin(2*numpy.pi*ns/N) # Single cycle in N points
v2 = numpy.linspace(1,0,N)      # Trigger edge
v2[0] = 0.5                     # But a little smoother...

# Send both waveforms at once
ao.push([v1,v2]) # Default is cyclic, pulse on the first output

# Enable the first input channel, enable it, and take data
ai = m2k.getAnalogIn()
ai.enableChannel(0, True)
ai.enableChannel(1, True)
ai.setSampleRate(100000000)
ai.setRange(0, libm2k.HIGH_GAIN)
ai.setRange(1, libm2k.HIGH_GAIN)

# Now try triggering
trig = ai.getTrigger()
trig.setAnalogMode(1,1)         # ch2, analog condition
trig.setAnalogSource(1)         # ch2
trig.setAnalogCondition(1,0)    # ch2, rising edge
trig.setAnalogLevel(0,0.5)      # ch2, 0.5V

# Set the timeout (5 sec) to be safe if it doesn't trigger
m2k.setTimeout(3000)

# Go for it
for n in range(10):
    y1, y2 = ai.getSamples(N*3)
    pylab.plot(y1)
    pylab.plot(y2)
