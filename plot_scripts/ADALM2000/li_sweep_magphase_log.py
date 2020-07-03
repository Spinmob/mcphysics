V1 = d['V1X']+1j*d['V1Y']
V2 = d['V2X']+1j*d['V2Y']

x = ( log10(d['f']) )
y = ( abs(V1), angle(V1)*180/pi, abs(V2), angle(V2)*180/pi )

xlabels = 'log10(Frequency (Hz))'
ylabels = ('V1 Mag (V)', 'V1 Phase (deg)', 'V2 Mag (V)', 'V2 Phase (deg)' )