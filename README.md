# McPhysics
Tools for the McGill University's undergraduate physics labs

## Recommended installation method

1. Download and install [Anaconda Python 3](https://www.anaconda.com/distribution/) or [Miniconda Python 3](https://docs.conda.io/en/latest/miniconda.html).

2. From the Anaconda Prompt (or system terminal, depending on your installation options), install the requisite packages available in the conda repository:
   ```
   conda install numpy scipy imageio matplotlib pyqtgraph spyder
   ```
   (You can also install these packages via anaconda-navigator, but why?)
3. Install spinmob and mcphysics via pip:
   ```
   pip install spinmob mcphysics
   ```
4. Open Spyder and start playing. Example script:
   ```
   import mcphysics
   mcphysics.playground.fitting_statistics_demo()
   ```
To upgrade to the latest version,
   ```
   pip install mcphysics --upgrade --no-cache-dir
   ```

## Organization
The McPhysics library is organized heirarchically, and you should use Spyder's code completion suggestions to navigate it. You can also type `<ctrl>-i` while your cursor is beside an object to access its documentation. Below is a list of the existing functionality as of 2019-04-19:

### mcphysics.data
 * __load_chn():__ Loads a Maestro .Chn file, returning a [spinmob databox](https://github.com/Spinmob/spinmob/wiki/2.-Data-Handling).
 * __load_chns():__ Load multiple .Chn files, returning a list of [spinmob databoxes](https://github.com/Spinmob/spinmob/wiki/2.-Data-Handling).
 * __plot_chn_files():__ Quick function for analyzing / plotting multiple .Chn files on the same axes.
 * __load_image():__ Loads an image file (jpg, png, etc...), returning 3d numpy array (1 dimension for x, 1 dimension for y, and 1 for the color channel).
 * __load_images():__ Loads multiple images, returning a list of such arrays.
 
 ### mcphysics.functions
  * __em_gaussian():__ Exponentially modified Gaussian probability density function.
  * __erfcx():__ A scaled complementary error function.
  * __reduced_chi2():__ Reduced chi^2 probability density function.
  * __voigt():__ Voigt probability density function.
 
 ### mcphysics.instruments
  * __sillyscope():__ Semi-unified graphical interface for interacting with an assortment of Rigol and Tektronix Oscilloscopes.
  * __sillyscope_command_line():__ Lower level, non-graphical interface.
  
 ### mcphysics.playground
  * __fitting_statistics_demo():__ Graphical fake data generator and fitter. Useful for visualizing fit statistics.
  * __plot_and_integrate_reduced_chi2():__ Plots the reduced chi^2 distribution for the specified degrees of freedom, then numerically integrates it. This is useful if you want to know how reasonable a given value of chi^2 is.
