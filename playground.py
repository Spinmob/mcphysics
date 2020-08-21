 # This file is part of the Macrospyn distribution 
 # (https://github.com/Spinmob/macrospyn).
 # Copyright (c) 2002-2020 Jack Childress (Sankey).
 # 
 # This program is free software: you can redistribute it and/or modify  
 # it under the terms of the GNU General Public License as published by  
 # the Free Software Foundation, version 3.
 # 
 # This program is distributed in the hope that it will be useful, but 
 # WITHOUT ANY WARRANTY; without even the implied warranty of 
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
 # General Public License for more details.
 # 
 # You should have received a copy of the GNU General Public License 
 # along with this program. If not, see <http://www.gnu.org/licenses/>.

import numpy       as _n
import scipy.stats as _stats

# For embedding matplotlib figures
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg    as _canvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as _navbar
from matplotlib.figure                  import Figure               as _figure

import mcphysics   as _m 
import spinmob     as _s
import spinmob.egg as _egg
_g = _egg.gui

import traceback as _traceback
_p = _traceback.print_last



def plot_and_integrate_reduced_chi2(dof=10, xmin=1e-6, xmax=5, steps=1e5):
    """
    Plots the reduced chi^2 density function, and then numerically integrates it.
    
    Parameters
    ----------
    dof=10
        Degrees of freedom.
    xmin, xmax, steps
        Plot range from xmin to xmax with the specified steps. This will affect
        the validity of the numerical integral.
    """
    
    _s.pylab.figure(100)
    a1 = _s.pylab.subplot(211)
    a2 = _s.pylab.subplot(212, sharex=a1)
    
    _s.plot.xy.function('f(x,dof)', xmin, xmax, steps, g=dict(f=_m.functions.reduced_chi2, dof=dof), 
                        axes=a1, ylabel='$P(\chi^2_r)$', xlabel='$\chi^2_r$', tall=True)
    _s.tweaks.integrate_shown_data(output_axes=a2, tall=True)
    _s.tweaks.ubertidy(window_size=[800,950])





class fitting_statistics_demo():
    
    """
    Graphical interface for generating fake data, fitting, and collecting 
    fit statistics.
    
    Parameters
    ----------
    block=True
        Whether to block the command line when the window is first shown.
    """
    
    
    def __init__(self, block=False):
        
        self._build_gui(block)

    def _build_gui(self, block_command_line=False):
        """
        Builds the GUI for taking fake data.
        """
        # Make a window with a left grid for settings and controls, and
        # a right grid for visualization.
        self.window = _g.Window('Fake Data Taker', size=[1000,700], autosettings_path='window.cfg')
        self.window.event_close = self.event_close
        self.grid_controls = self.window.place_object(_g.GridLayout(False))
        self.grid_plotting = self.window.place_object(_g.GridLayout(False), alignment=0)
        
        # Add the acquire button & connect the signal
        self.button_acquire = self.grid_controls.place_object(_g.Button('Acquire'),    alignment=0).set_width(70)
        self.button_fit     = self.grid_controls.place_object(_g.Button('Fit')    ,    alignment=0).set_width(55)
        self.button_loop    = self.grid_controls.place_object(_g.Button('Loop', True), alignment=0).set_width(55)
        self.button_clear   = self.grid_controls.place_object(_g.Button('Clear'),      alignment=0).set_width(55)
        self.button_acquire.signal_clicked.connect(self.button_acquire_clicked)
        self.button_fit    .signal_clicked.connect(self.button_fit_clicked)
        self.button_loop   .signal_clicked.connect(self.button_loop_clicked)
        self.button_clear  .signal_clicked.connect(self.button_clear_clicked)
        
        # Create an populate the settings tree
        self.grid_controls.new_autorow()
        self.tree_settings  = self.grid_controls.place_object(_g.TreeDictionary(), column_span=4)
        
        self.tree_settings.add_parameter('Acquire/reality', '1.7*x+1.2')
        self.tree_settings.add_parameter('Acquire/x_noise',        0)
        self.tree_settings.add_parameter('Acquire/y_noise',      1.3)
        
        self.tree_settings.add_parameter('Acquire/xmin',    0)
        self.tree_settings.add_parameter('Acquire/xmax',   10)
        self.tree_settings.add_parameter('Acquire/steps', 100, dec=True)
        
        self.tree_settings.add_parameter('Fit/function',   'a*x+b')
        self.tree_settings.add_parameter('Fit/parameters', 'a=0,b=0')
        self.tree_settings.add_parameter('Fit/assumed_ey', 1.3)
        
        self.tree_settings.add_parameter('Stats/bins',        14)
        self.tree_settings.add_parameter('Stats/versus_x',    'a')
        self.tree_settings.add_parameter('Stats/versus_y',    'b')
        self.tree_settings.add_parameter('Stats/plot_theory', False)
        
        # Add the tabs and plotter to the other grid
        self.tabs_plotting = self.grid_plotting.place_object(_g.TabArea('tabs_plotting.cfg'), alignment=0)
        
        # Tab for raw data
        self.tab_raw  = self.tabs_plotting.add_tab('Raw Data')
        self.plot_raw = self.tab_raw.place_object(
                _g.DataboxPlot(autosettings_path='plot_raw.cfg', autoscript=1), 
                alignment=0)
        self.plot_raw.autoscript_custom = self._autoscript_raw
        
        # Tab for fit
        self.tab_fit    = self.tabs_plotting.add_tab('Fit')
        
        self.figure_fit = _figure()
        self.canvas_fit = _canvas(self.figure_fit)
        self.navbar_fit = _navbar(self.canvas_fit, self.window._widget)
        
        self.tab_fit.place_object(self.navbar_fit, alignment=0)
        self.tab_fit.new_autorow()
        self.tab_fit.place_object(self.canvas_fit, alignment=0)

        # Fitter object linked to this figure canvas
        self.fitter = _s.data.fitter()
        self.fitter.set(autoplot=False)
        self.fitter.figures = [self.figure_fit]

        # Tab for running total of fit parameters
        self.tab_parameters  = self.tabs_plotting.add_tab('Fit Parameters')
        self.plot_parameters = self.tab_parameters.place_object(
                _g.DataboxPlot(autosettings_path='plot_parameters.cfg'),
                alignment=0)
        # Give it a handle on the fitter for the script
        self.plot_parameters.fitter = self.fitter
        
        # Tab for histograms
        self.tab_stats    = self.tabs_plotting.add_tab('Histograms')
        
        self.figure_stats = _figure()
        self.canvas_stats = _canvas(self.figure_stats)
        self.navbar_stats = _navbar(self.canvas_stats, self.window._widget)
        
        self.tab_stats.place_object(self.navbar_stats, alignment=0)
        self.tab_stats.new_autorow()
        self.tab_stats.place_object(self.canvas_stats, alignment=0)
        
        # Changing tabs can update plots
        self.tabs_plotting.signal_switched.connect(self.tabs_plotting_switched)
        
        # Set up the autosave & load.
        self.tree_settings.connect_any_signal_changed(self.tree_settings.autosave)
        self.tree_settings.connect_any_signal_changed(self.update_all_plots)
        self.tree_settings.load()
        
        # Show the window
        self.window.show(block_command_line)
    
    def _autoscript_raw(self):
        """
        Returns a nice custom autoscript for plotting the raw data.
        """
        return "x = [ d[0] ]\ny = [ d[1] ]\n\nxlabels = 'x'\nylabels = ['y']"
    
    def tabs_plotting_switched(self, *a):
        """
        Someone switched a tab!
        """
        if   a[0]==1: self.update_fit_plot()
        elif a[0]==3: self.update_histograms_plot()
    
    def button_acquire_clicked(self, *a):
        """
        Acquires fake data and dumps it with the header into the plotter.
        """
        
        # Dump the header info
        self.tree_settings.send_to_databox_header(self.plot_raw)
        
        # Generate the data
        x = _n.linspace(self.tree_settings['Acquire/xmin'], 
                        self.tree_settings['Acquire/xmax'],
                        self.tree_settings['Acquire/steps'])
        
        
        d = _s.fun.generate_fake_data(self.tree_settings['Acquire/reality'], x,
                                      self.tree_settings['Acquire/y_noise'],
                                      self.tree_settings['Acquire/x_noise'])
        
        # Dump it to the plotter and plot
        self.plot_raw.copy_columns(d)
        
        # Plot it.
        self.plot_raw.plot()
        
        # Autosave if checked
        self.plot_raw.autosave()
    
    def button_fit_clicked(self,*a):
        """
        Assuming there is data, run the fit!
        """
        # Set the functions
        self.fitter.set_functions(self.tree_settings['Fit/function'],
                                  self.tree_settings['Fit/parameters'])
        
        # Set the data
        self.fitter.set_data(self.plot_raw[0], self.plot_raw[1], 
                             self.tree_settings['Fit/assumed_ey'])
        
        # Fit!
        self.fitter.fit()
        
        # Draw
        self.figure_fit.canvas.draw()
        self.window.process_events()
        
        # Now append the fit results to the next tab's plotter
        ps  = self.fitter.results.params
        x2  = self.fitter.get_reduced_chi_squared()
        dof = self.fitter.get_degrees_of_freedom()
        
        ckeys = ['reduced_chi2', 'DOF']
        row   = [x2,dof]
        for pname in ps:
            
            # Append the fit parameter
            ckeys.append(pname)
            row  .append(ps[pname].value)

            # Append the fit error
            ckeys.append(pname+'_error')
            row  .append(ps[pname].stderr)
        
        # If the parameters haven't changed, just append the data
        self.plot_parameters.append_row(row, ckeys=ckeys)
        
        # If this is the first row, set up the histograms
        if len(self.plot_parameters[0]) == 1:
            
            # PARAMETERS: Send the settings to the header
            self.tree_settings.send_to_databox_header(self.plot_parameters)
            
            # Generate a plot script
            s = 'x = [None]\ny = [d[0],d[1]'
            for n in range(len(ps)):
                s = s+',d['+str(2*n+2)+']'
            
            s = s+']\n\nxlabels = "Iteration"\nylabels = [ d.ckeys[0], d.ckeys[1]'
            for n in range(len(ps)):
                s = s+',d.ckeys['+str(2*n+2)+']'
            s = s+']'
            
            # Set to manual script and update the text
            self.plot_parameters.combo_autoscript.set_value(0, block_signals=True)
            self.plot_parameters.script.set_text(s)
            
            # HISTOGRAMS: Clear the figure and set up the histogram axes
            self.axes_histograms = []
            self.figure_stats.clear()
        
            # Calculate how many rows of plots are needed
            rows = int(_n.ceil(len(ps)*0.5)+1)
        
            # Reduced chi^2 histogram
            self.axes_histograms.append(self.figure_stats.add_subplot(rows, 2, 1))
            self.axes_histograms.append(self.figure_stats.add_subplot(rows, 2, 2))
        
            # Parameter histograms
            for n in range(len(ps)):
                self.axes_histograms.append(self.figure_stats.add_subplot(rows, 2, n+3))
                    
        # Update the parameters plot!
        self.plot_parameters.plot()
        
        # If we're on the fit or stats tab (these are slow to plot)
        if self.tabs_plotting.get_current_tab()==1: self.update_fit_plot()
        if self.tabs_plotting.get_current_tab()==3: self.update_histograms_plot()
        
    def button_loop_clicked(self, value):
        """
        When someone clicks the "loop" button. 
        """
        # If it's enabled, start the loop
        if not value: return
    
        # Run the loop
        while self.button_loop.is_checked():
            
            # Acquire data and fit
            self.button_acquire_clicked(True)
            self.window.process_events()
            self.button_fit_clicked(True)
            self.window.process_events()
    
    def button_clear_clicked(self, *a):
        """
        Someone clears the data.
        """
        self.plot_parameters.clear()
        self.update_all_plots()
    
    def update_fit_plot(self):
        """
        Update the fit plot.
        """
        if not self.tabs_plotting.get_current_tab()==1: return
        
        self.fitter.plot()
        self.window.process_events()
        self.figure_fit.canvas.draw()
        self.window.process_events()
    
    def update_histograms_plot(self):
        """
        Update the histogram plots (actually perform the histogram and plot).
        """
        # Don't bother if we're not looking.
        if not self.tabs_plotting.get_current_tab()==3: return
        
        if len(self.plot_parameters) and len(self.axes_histograms):
            
            # Update the chi^2 histogram histograms
            self.axes_histograms[0].clear()
            N,B,c = self.axes_histograms[0].hist(self.plot_parameters[0], self.tree_settings['Stats/bins'], label='$\chi^2_{reduced}$')
            x = (B[1:]+B[:-1])*0.5
            
            # Include the error bars
            self.axes_histograms[0].errorbar(x, N, _n.sqrt(N), ls='', marker='+')
            
            # Tidy up
            self.axes_histograms[0].set_xlabel('$\chi^2_{reduced}$')
            self.axes_histograms[0].set_ylabel('Counts')
            
            # Plot the expected distribution.
            if self.tree_settings['Stats/plot_theory']:
                
                x2  = _n.linspace(min(0.5*(B[1]-B[0]),0.02), max(1.5,max(self.plot_parameters[0])), 400)
                dof = self.plot_parameters[1][-1]
                pdf = len(self.plot_parameters[1]) * dof * _stats.chi2.pdf(x2*dof,dof) * (B[1]-B[0])                
                self.axes_histograms[0].plot(x2,pdf,label='Expected ('+str(dof)+ 'DOF)')
                self.axes_histograms[0].legend()
            
            # Include zero, to give a sense of scale.
            self.axes_histograms[0].set_xlim(0,max(1.5,max(self.plot_parameters[0]))*1.05)
            
            
            # Plot the correlations
            self.axes_histograms[1].clear()
            self.axes_histograms[1].plot(self.plot_parameters[self.tree_settings['Stats/versus_x']],
                                         self.plot_parameters[self.tree_settings['Stats/versus_y']],
                                         label=self.tree_settings['Stats/versus_y']+' vs '+self.tree_settings['Stats/versus_x'],
                                         linestyle='', marker='o', alpha=0.3)
            self.axes_histograms[1].set_xlabel(self.tree_settings['Stats/versus_x'])
            self.axes_histograms[1].set_ylabel(self.tree_settings['Stats/versus_y'])
            self.axes_histograms[1].legend()
            
            # Now plot the distributions of the other fit parameters.
            for n in range(len(self.fitter.p_fit)):
                
                # Plot the histogram
                self.axes_histograms[n+2].clear()
                N,B,c = self.axes_histograms[n+2].hist(self.plot_parameters[2*n+2], self.tree_settings['Stats/bins'], label=self.fitter.get_parameter_names()[n])
                x = (B[1:]+B[:-1])*0.5
                
                # Include the error bars
                self.axes_histograms[n+2].errorbar(x, N, _n.sqrt(N), ls='', marker='+')
            
                # Tidy up
                self.axes_histograms[n+2].set_xlabel(self.fitter.get_parameter_names()[n])
                self.axes_histograms[n+2].set_ylabel('Counts')
                
                # Plot the expected distribution, calculated from the mean
                # and fit error bar.
                if self.tree_settings['Stats/plot_theory']:
                    
                    x0  = _n.average(self.plot_parameters[2*n+2]) 
                    ex  = self.plot_parameters[2*n+3][-1]
                    x   = _n.linspace(x0-4*ex, x0+4*ex, 400)
                    pdf = len(self.plot_parameters[1]) * _stats.norm.pdf((x-x0)/ex)/ex * (B[1]-B[0])
                    
                    self.axes_histograms[n+2].plot(x,pdf,label='Expected')
                    self.axes_histograms[n+2].legend()
                
        
        self.figure_stats.canvas.draw()
        self.window.process_events()
        
    def update_all_plots(self, *a):
        """
        Updates the Fit and Stats plots.
        """
        self.update_fit_plot()
        self.update_histograms_plot()
    
    def event_close(self, *a):
        """
        Quits acquisition when the window closes.
        """
        self.button_loop.set_checked(False)
        
        
if __name__ == '__main__':
    import os as _os
    import shutil as _sh
    if _os.path.exists('egg_settings'): _sh.rmtree('egg_settings')

    
    self = fitting_statistics_demo()