# McPhysics

![](https://raw.githubusercontent.com/wiki/Spinmob/spinmob/Egg/10-dark-theme.png)

This is a library of tools spefically aimed at the McGill undergraduate physics labs, namely PHYS 359/469 at the moment. It can be thought of as an augmentation of the [Spinmob](https://github.com/Spinmob/spinmob/wiki) library, which provides general-purpose, broadly applicable data handling, plotting, fitting, graphical interface, and other analysis tools. 

The installation discussed below automatically installs Spinmob, and you can read the [Spinmob wiki](https://github.com/Spinmob/spinmob/wiki), which provides a lot of information about Python, data handling, automated fitting, and graphical interface building.

## Recommended installation method

Below is the standard installation method that works most reliably. Note many people already have a conda python installation and either do not want to mess with it or cannot make the following installation work due to library conflicts; in these cases, we recommend [creating a new conda environment](https://github.com/Spinmob/mcphysics#creating-and-activating-a-new-environment) as discussed below.

1. Download and install [Miniconda Python 3](https://docs.conda.io/en/latest/miniconda.html) or the full bloaty [Anaconda Python 3](https://www.anaconda.com/). See additional instructions below for OSX. 

2. From the Anaconda Prompt (or system terminal, depending on your installation options), install the "core" packages:
   ```
   conda install pip spyder pyqtgraph
   ```
   then
   ```
   pip install spinmob mcphysics imageio sounddevice
   ```

3. Open Spyder and start playing. Example script:
   ```
   import mcphysics
   mcphysics.playground.fitting_statistics_demo()
   ```

## OSX Notes
You may need to tell your system where Anaconda's `bin` folder is located manually. A method that worked is to create a text file named `.bash_profile` in your home directory, and add the line `export PATH="/path/to/Anaconda3/bin:$PATH"`, replacing `/path/to/Anaconda3` with the appropriate location of the `bin` folder. Log out and back in, and the terminal should now "know about" `conda` and `pip`.

## Creating and Activating a New Environment

If you wish to create a completely "clean" conda environment, you can do so with the following commands. Once a new environment is activated, you can then install packages as discussed above.

1. To create a clean environment named `pants`, use the command below (following the resulting instructions):
   ```
   conda create --name pants
   ```
   
2. To activate the environment:
   ```
   conda activate pants
   ```

3. To see which environments exist and which is activated (has a `*` next to it):
   ```
   conda env list
   ```
   
## Upgrading
To upgrade to the latest stable versions,
   ```
   pip install mcphysics spinmob --upgrade --no-cache-dir
   ```

## Optional instrument drivers

If you need to talk to the supported equipment, you may also need to install some drivers.

### VISA and serial instruments
To access VISA-based instruments (see below) you will also need a "standard" VISA driver, such as Rhode & Schwartz VISA or National Instruments VISA. I recommend [Rhode & Schwarz](https://www.rohde-schwarz.com/ca/driver-pages/remote-control/3-visa-and-tools_231388.html) because it's lightweight and works with everything we've tested. You will then need to run `pip install pyvisa pyserial` to get python access.

### ADALM2000
To access an ADALM2000, you will need to install [libiio](https://github.com/analogdevicesinc/libiio) and [libm2k (with python bindings!)](https://github.com/analogdevicesinc/libm2k). On Windows, you will also need the [m2k driver](https://github.com/analogdevicesinc/plutosdr-m2k-drivers-win/releases), and you may have to download the appropriate `*.whl` file for your system, then manually run a `pip install [filename].whl` from the anaconda prompt to get it into python. On Linux (and probably osx), we are required to manually compile the libm2k library, so McPhysics may require a specific version to be installed. If this is the case, `import mcphysics` should complain and tell you which version is required when you try to access the device.

### Fancy sound cards
Fancy sound cards may require their own drivers to be installed, but do not need anything more than the `sounddevice` library, which is installed by default above.

## Organization
The McPhysics library is organized heirarchically, and you should use Spyder's code completion suggestions to navigate it. You can also type `<ctrl>-i` while your cursor is beside an object to access its documentation. Below is a list of the existing functionality. All of these objects are documented within the code itself, and detailed help is available via python's `help()` command or your favorite IDE's or ipython's built in help / autocomplete functionality. An introduction to some of the complex items is available on our (growing) [wiki](https://github.com/Spinmob/mcphysics/wiki).

### mcphysics.data
 * __load_chn():__ Loads a Maestro .Chn file, returning a [spinmob databox](https://github.com/Spinmob/spinmob/wiki/2.-Data-Handling).
 * __load_chns():__ Load multiple .Chn files, returning a list of [spinmob databoxes](https://github.com/Spinmob/spinmob/wiki/2.-Data-Handling).
 * __load_chns_directory():__ Performs `load_chns()` on all the .Chn files in a selected directory.
 * __plot_chns():__ Shortcut function for analyzing / plotting multiple .Chn files on the same axes.
 * __plot_chns_directory():__ Performs `plot_chns()` on all the .Chn files in a selected directory.
 * __convert_chn_to_csv():__ Loads multiple .Chn files, converts them to csv, and dumps them in a directory of your choice.
 * __load_image():__ Loads an image file (jpg, png, etc...), returning 3d numpy array (1 dimension for x, 1 dimension for y, and 1 for the color channel).
 * __load_images():__ Loads multiple images, returning a list of such arrays.
 
 ### mcphysics.functions
  * __em_gaussian():__ Exponentially modified Gaussian probability density function.
  * __gaussian():__ Gaussian probability density function.
  * __gaussian_cdf():__ Cumulative density function (running integral) of the above Gaussian probability density function.
  * __reduced_chi2():__ Reduced chi^2 probability density function.
  * __voigt():__ Voigt probability density function.
 
 ### mcphysics.instruments
  * __[adalm2000()](https://github.com/Spinmob/mcphysics/wiki/instruments.adalm2000) (requires m2k drivers and libraries):__ Scriptable graphical interface for the ADALM2000 multifunction DAQ.
  * __adalm2000_api() (requires m2k drivers and libraries):__ Lower level, non-graphical interface for the ADALM2000.
  * __[auber_syl53x2p](https://github.com/Spinmob/mcphysics/wiki/instruments.auber_syl53x2p):__ Scriptable graphical interface for an Auber SYL-53X2P temperature controller.
  * __auber_syl53x2p_apo():__ Lower level, non-graphical interface for the Auber SYL-53X2P.
  * __[keithley_dmm()](https://github.com/Spinmob/mcphysics/wiki/instruments.keithley_dmm) (requires VISA):__ Graphical interface for our the Keithley digital multimeters (currently 199).
  * __keithley_dmm_api() (requires VISA):__ Lower level, non-graphical interface for the DMM.
  * __[sillyscope() (requires VISA)](https://github.com/Spinmob/mcphysics/wiki/instruments.sillyscope):__ Semi-unified graphical interface for interacting with an assortment of Rigol and Tektronix sillyscopes.
  * __sillyscope_api() (requires VISA):__ Lower level, non-graphical interface for the same sillyscopes.
  * __[soundcard()](https://github.com/Spinmob/mcphysics/wiki/instruments.soundcard):__ Scriptable graphical interface for interacting with sound cards.
  
 ### mcphysics.playground
  * __[fitting_statistics_demo()](https://github.com/Spinmob/mcphysics/wiki/playground.fitting_statistics_demo):__ Graphical fake data generator and fitter. Useful for visualizing fit statistics.
  * __plot_and_integrate_reduced_chi2():__ Plots the reduced chi^2 distribution for the specified degrees of freedom, then numerically integrates it. This is useful if you want to know how reasonable a given value of chi^2 is.

 ### mcphysics.experiments
 Some of the experiments have a collection of the above tools, along with some additional tools specific to the experiment:
 
  * __[alpha.arduino()](https://github.com/Spinmob/mcphysics/wiki/experiments.alpha.arduino):__ Graphical front-end for the specific Arduino controllers connected to the Alpha Decay experiments.
  * __[drum.motors_api()](https://github.com/Spinmob/mcphysics/wiki/experiments.drum.motors_api)__: Scripted interface for controlling the stepper motors via the attached Arduino.
