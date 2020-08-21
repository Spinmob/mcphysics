import mcphysics
import libm2k, pylab, numpy, time

# Set the output buffer size (No), and rate
No      = 280      # <-------- This needs to be a multiple of 4 to work right
ao_rate = 75000.0

# Stable buffer sizes seem to be multiples of 4.
# Tested to show no beating: No = 260, 264, 268, 272, 276, 280, ..., 300

# Get a reasonable frequency.
f = ao_rate/No * 8   # 11 complete cycles in 275 points at 3 kHz
print('Frequency =', f)


# Get the first m2k name
name = libm2k.getAllContexts()[0]

# Get the m2k
m2k = libm2k.m2kOpen(name).toM2k()

# Run the calibration
m2k.calibrate()

# Enable the outputs and set the rates.
ao = m2k.getAnalogOut()
ao.enableChannel(0, True)
ao.enableChannel(1, True)
ao.setSampleRate(0, ao_rate)
ao.setSampleRate(1, ao_rate)

# Create waveform arrays: sinusoid and square pulse
#
# 75 kHz sampling rate: 2 kHz good,

# 3 kHz, 275 samples bad
ns = numpy.linspace(0,No-1,No) # List of integers
ts = ns/ao_rate                # Time array
v1 = numpy.sin(2*numpy.pi*f*ts)

# Send both waveforms at once
ao.push([v1,v1]) # Default is cyclic

# Enable the first input channel, enable it, and take data
ai_rate = 100000.0
ai = m2k.getAnalogIn()
ai.enableChannel(0, True)
ai.enableChannel(1, True)
ai.setSampleRate(ai_rate)
ai.setRange(0, libm2k.HIGH_GAIN)
ai.setRange(1, libm2k.HIGH_GAIN)

# Set the timeout (1 sec) so it collects without trigger
m2k.setTimeout(1000)

# Let it settle
time.sleep(0.1)

# Get 100 ms of data
Ni = int(0.1*ai_rate)
y1, y2 = ai.getSamples(Ni)

# Get the time-domain
ts = numpy.linspace(0, (Ni-1)/ai_rate, Ni)
pylab.plot(ts, y1, label='analog in')

# Get expected curve
ye = numpy.sin(2*numpy.pi*f*ts)
pylab.plot(ts, ye+2.0, label='expected')

# Plot sum to see the beating
pylab.plot(ts, ye+y1+5.0, label='sum')

pylab.legend()
pylab.xlabel('Time (s)')
pylab.ylabel('Voltage plus artificial offsets (V)')