import spinmob as _s
import time    as _t
import struct  as _struct
import numpy   as _n
import os      as _os




def load_chn(path=None):
    """
    Loads a Maestro CHN file at the specified path. Will return a databox with all 
    the information.
    
    Parameters
    ----------
    path=None
        If None, a dialog will pop up. Otherwise specify a valid path (string).
    """
    if path==None: path = _s.dialogs.load(filters="*.Chn")
    if path==None: return
    
    # Create a databox
    d = _s.data.databox()
    
    # Open the file
    fh = open(path,mode="rb")
    
    # Read the buffer
    buffer = fh.read()
    
    # Unpack
    [type, unitnumber, segment_number] = _struct.unpack("hhh",buffer[0:6])
    ascii_seconds = buffer[6:8].decode()
    [real_time_20ms, live_time_20ms] = _struct.unpack("ii",buffer[8:16])
    start_date = buffer[16:24].decode()
    start_time = buffer[24:28].decode()
    [channel_offset, channel_count] = _struct.unpack("hh",buffer[28:32])
    
    # Get the counts data
    spectrum = _n.zeros(channel_count,dtype=int)
    for i in range(channel_count): [spectrum[i]] = _struct.unpack("I",buffer[32+4*i:36+4*i])
    d['Channel'] = range(channel_count)
    d['Counts']  = spectrum
    
    # Get the date in a nice format
    if "1" == start_date[7]: century = 20
    else:                    century = 19
    start_RFC2822 = "%s %s %02d%s %s:%s:%s" % (start_date[0:2], start_date[2:5], century, start_date[5:7], start_time[0:2], start_time[2:4], ascii_seconds)
    
    # Header info
    d.path=path
    d.h(path=path)
    d.h(start_time = _t.strptime(start_RFC2822,"%d %b %Y %H:%M:%S"))
    d.h(real_time = 0.02*real_time_20ms)
    d.h(live_time = 0.02*live_time_20ms)
    
    return d

def load_chns(paths=None):
    """
    Loads multiple chn files, returning a list of databoxes.
    
    Parameters
    ----------
    paths=None
        If None, a dialog will pop up, allowing you to select multiople files.
        Otherwise, specify a valid *list* of paths, e.g. ['C:/test/path.chn', 'C:/test/path2.chn']
    """
    if paths==None: paths=_s.dialogs.load_multiple(filters='*.Chn')
    if paths==None: return
    
    ds = []
    for path in paths: ds.append(load_chn(path))
    return ds

def plot_chn_files(xscript='d[0]', yscript='d[1]', eyscript='sqrt(d[1])', marker='+', linestyle='', xlabel='Channel', ylabel='Counts', paths=None, **kwargs):
    """
    Opens a bunch of chn files and plots the specified script for each. You can
    get the same result by loading multiple chn files (returns a list of databoxes)
    and sending the result to spinmob.plot.xy.databoxes().
    
    Arguments
    ---------
    xscript, yscript, eyscript
        Scripts for creating the xdata, ydata, and error bars. These follow the
        convention of spinmob.plot.xy.files(). Any valid python string evaluating to
        an array of numbers will work. "d" refers to the databox being plotted, and
        the system "knows" about all numpy functions. Specifying None for xscript
        or yscript will generate integer arrays to match the other data sets.
    
    marker, linestyle, xlabel, ylabel
        Some common plot options.
    
    Additional optional keyword arguments are sent to spinmob.plot.databoxes,
    spinmob.plot.data, and pylab.errorbar.
    """
    if paths==None: paths = _s.dialogs.load_multiple(filters='*.Chn')
    if paths==None: return
    
    # Load the files
    ds = load_chns(paths)
    
    # Get the title
    title = _os.path.split(ds[0].path)[0]
    
    _s.plot.xy.databoxes(ds, xscript, yscript, eyscript, 
                         marker=marker, linestyle=linestyle, 
                         xlabel=xlabel, ylabel=ylabel, 
                         title=title, **kwargs)
    


# Only import this if imageio is installed
try:
    import imageio as _imageio
    
    def load_image(path=None):
        """
        Loads an image, returning a 3D array: two indices for the pixel position
        (x and y), and one index for the color, which can have either 3 values
        (RGB) or 4 (RGBA), depending on the file format.
        
        Parameters
        ----------
        path=None
            If None, a dialog will open up. Otherwise, specify a valid path (string).
        
        """
        if path == None: path = _s.dialogs.load()
        if path == None: return
        
        # Load the image into array "a". 
        return _imageio.imread(path)
        
    
    def load_images(paths=None):
        """
        Loads multiple images, returning a list of 3D arrays, as per load_image.
        
        Parameters
        ----------
        paths=None
            If None, a dialog will pop up. Otherwise, specify a *list* of valid
            paths to images.
        """
        if paths == None: paths = _s.dialogs.load_multiple()
        if paths == None: return
        
        arrays = []
        for path in paths: arrays.append(load_image(path))
        return arrays

except:
    print("Note: Image loading is disabled. You may need to install imageio, which can be done with the command 'conda install imageio' from the system terminal or anaconda prompt. You can also find it in anaconda-navigator.")