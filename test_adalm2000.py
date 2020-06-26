import mcphysics as _mp; libm2k = _mp._m2k

# import libm2k
import pylab

# Get the first m2k name
name = libm2k.getAllContexts()[0]

# Get the m2k
m2k = libm2k.m2kOpen(name).toM2k()

# Run the calibration
m2k.calibrate()

# Output waveform characteristics
N  = 1000 # Number of repetitions per voltage (adjusts sample rate, too)
V1 = 1.0  # Voltage step 1
V2 = 2.0  # Voltage step 2

# Enable the first output, enable it, and send it some data.
ao = m2k.getAnalogOut()
ao.enableChannel(0, True)
ao.setSampleRate(0, 750*N)
ao.push(0, [0]*N+[V1]*N+[0]*N+[V2]*N) # Default is cyclic

# Enable the first input channel, enable it, and take data
ai = m2k.getAnalogIn()
ai.enableChannel(0, True)
ai.setSampleRate(1000000)
vs = ai.getSamples(7000)

# Plot it.
pylab.plot(vs[0])

# Wait for the user to click the plot
pylab.ginput()

# Now try triggering
trig = ai.getTrigger()
trig.setAnalogMode(0,1)         # ch1, analog condition
trig.setAnalogSource(0)         # ch1
trig.setAnalogCondition(0,0)    # ch1, rising edge
trig.setAnalogLevel(0,1.5)      # ch1, 0.5V

# Set the timeout (5 sec) to be safe if it doesn't trigger
m2k.setTimeout(5000)

# Go for it
pylab.plot(ai.getSamples(7000)[0])
