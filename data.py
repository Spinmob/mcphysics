import spinmob   as _s
import time      as _t
import struct    as _struct
import numpy     as _n
import os        as _os
import mcphysics as _mp
import glob      as _glob




def load_chn(path=None, **kwargs):
    """
    Loads a Maestro CHN file at the specified path. Will return a databox with all
    the information.

    Parameters
    ----------
    path=None
        If None, a dialog will pop up. Otherwise specify a valid path (string).

    Optional keyword arguments, e.g., delimeter=',', are sent to spinmob.data.databox()
    """
    if path==None: path = _s.dialogs.load(filters="*.Chn")
    if path==None: return

    # Create a databox
    d = _s.data.databox(**kwargs)

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

    # Get the byte offset of the data
    offset = 36+4*(channel_count-1)

    # Get the size of the "Sample description" string
    info_size = int.from_bytes( buffer[offset+320:offset+321], "big" )

    # Extract "Sample description" string
    info = buffer[offset+321:offset+321+info_size].decode()

    d['Channel'] = range(channel_count)
    d['Counts']  = spectrum

    # Get the date in a nice format
    if "1" == start_date[7]: century = 20
    else:                    century = 19
    start_RFC2822 = "%s %s %02d%s %s:%s:%s" % (start_date[0:2], start_date[2:5], century, start_date[5:7], start_time[0:2], start_time[2:4], ascii_seconds)
    s = _t.strptime(start_RFC2822,"%d %b %Y %H:%M:%S")
    start = dict(
        year     = s.tm_year,
        month    = s.tm_mon,
        day      = s.tm_mday,
        hour     = s.tm_hour,
        minute   = s.tm_min,
        second   = s.tm_sec,
        year_day = s.tm_yday)

    # Header info
    d.path=path
    d.h(description = info,
        start_time  = start,
        real_time   = 0.02*real_time_20ms,
        live_time   = 0.02*live_time_20ms,
        path        = path,)

    return d

def load_chns(paths=None, combine=False, **kwargs):
    """
    Loads multiple chn files, returning a list of databoxes.

    Parameters
    ----------
    paths=None : list of paths
        If None, a dialog will pop up, allowing you to select multiople files.
        Otherwise, specify a valid *list* of paths, e.g. ['C:/test/path.chn', 'C:/test/path2.chn']
    
    combine=False : bool
        If True, the counts from all files will be summed into a single databox, rather
        than returning a list of databoxes. The header of the returned databox
        will be the header of the first file in the list.

    Optional keyword arguments (e.g., delimiter=',') are sent to load_chn()
    """
    if paths==None: paths=_s.dialogs.load_multiple(filters='*.Chn')
    if paths==None: return

    ds = []
    for path in paths: ds.append(load_chn(path, **kwargs))

    # If we're not combining    
    if not combine: return ds
    
    # Otherwise, make a master databox.
    dm = ds.pop(0)
    for d in ds: dm[1] += d[1]
    
    return dm

def plot_chns(xscript='d[0]', yscript='d[1]', eyscript='sqrt(d[1])', marker='+', linestyle='', xlabel='Channel', ylabel='Counts', paths=None, combine=False, **kwargs):
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
        
    combine=False : bool
        If True, will sum the selected data into a single curve.

    Additional optional keyword arguments are sent to spinmob.plot.xy.databoxes,
    spinmob.plot.xy.data, and pylab.errorbar.
    """
    if paths==None: paths = _s.dialogs.load_multiple(filters='*.Chn')
    if paths==None: return

    # Load the files
    ds = load_chns(paths, combine)
    
    # If it's combined
    if not type(ds) is list: ds = [ds]

    # Get the title
    title = _os.path.split(ds[0].path)[0]

    _s.plot.xy.databoxes(ds, xscript, yscript, eyscript,
                         marker=marker, linestyle=linestyle,
                         xlabel=xlabel, ylabel=ylabel,
                         title=title, **kwargs)

def load_chns_directory(path=None, **kwargs):
    """
    Calls load_chns() on all the *.Chn files in the specified directory.
    
    Parameters
    ----------
    path=None : str
        Optional directory. If None, a dialog will pop up to ask for a directory.
        
    Additional keyword arguments are sent to load_chns()
    
    Returns
    -------
    The result of load_chns()
    """
    if path is None: path = _s.dialogs.select_directory('Select a directory containing Chn files!')
    if path is None: return
    
    paths = _glob.glob(_os.path.join(path,'*.Chn'))
    return load_chns(paths, **kwargs)
    
def plot_chns_directory(path=None, **kwargs):
    """
    Calls plot_chns() on all the *.Chn files in the specified directory.
    
    Parameters
    ----------
    path=None : str
        Optional directory. If None, a dialog will pop up to ask for a directory.
        
    Additional keyword arguments are sent to plot_chns()
    
    Returns
    -------
    The result of plot_chns()
    """
    if path is None: path = _s.dialogs.select_directory('Select a directory containing Chn files!')
    if path is None: return
    
    paths = _glob.glob(_os.path.join(path,'*.Chn'))
    return plot_chns(paths=paths, **kwargs)
    

def convert_chn_to_csv(chn_paths=None, output_dir=None):
    """
    Opens the supplied Maestro Chn files and saves them as csv

    Parameters
    ----------
    chn_paths=None : list of strings
        List of paths to Chn files. If None, this will pop up a dialog.

    output_dir=None: string
        Path to output directory. If None, this will pop up a dialog.
    """
    ds = load_chns(chn_paths, delimiter=',')
    if ds is None: return

    if output_dir is None: output_dir = _s.dialogs.select_directory('Select an output directory.')
    if output_dir is None: return

    for d in ds:

        # Get the file name
        filename = _os.path.split(d.path)[-1]

        # Replace the extension
        s = filename.split('.')
        s[-1] = 'csv'
        filename = '.'.join(s)

        # Save it
        d.save_file(_os.path.join(output_dir, filename))

    return ds


# Only import this if imageio is installed
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
    if not _mp._imageio: raise Exception('You need to install imageio for this function.')

    if path == None: path = _s.dialogs.load()
    if path == None: return

    # Load the image into array "a".
    return _mp._imageio.imread(path)


def load_images(paths=None):
    """
    Loads multiple images, returning a list of 3D arrays, as per load_image.

    Parameters
    ----------
    paths=None
        If None, a dialog will pop up. Otherwise, specify a *list* of valid
        paths to images.
    """
    if not _mp._imageio: raise Exception('You need to install imageio for this function.')

    if paths == None: paths = _s.dialogs.load_multiple()
    if paths == None: return

    arrays = []
    for path in paths: arrays.append(load_image(path))
    return arrays


