x = log10(d['f(Hz)']); xlabels = 'log10( Frequency (Hz) )'
y = [];                ylabels = []
for n in range(2,len(d),2):
    z = d[n]+1j*d[n+1]; l = d.ckeys[n][0:len(d.ckeys[n])-2]
    y      .append(abs(z));   ylabels.append(  'Mag('+l+')')
    y      .append(angle(z)); ylabels.append('Phase('+l+')')