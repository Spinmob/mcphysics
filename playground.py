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
import time as _t

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

    def _build_gui(self, block=False):
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
        
        self.button_loop.set_colors_checked('white', 'red')
        
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
                _g.DataboxPlot(autosettings_path='plot_parameters.cfg', show_logger=True),
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
        self.window.show(block)
    
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
        

class geiger_simulation():
    """
    Graphical interface for simulating a Geiger counter.
    
    Parameters
    ----------
    block=False : bool
        Whether to block the console while the window is open.
    """
    def __init__(self, name='geiger_simulation', block=False):
        
        self.name   = name
        self.exception_timer = _g.TimerExceptions()
        
        # Assemble the main layout
        self.window = _g.Window('Geiger Simulation', autosettings_path=name+'.window', size=[900,700])
        self.grid_top = gt = self.window.add(_g.GridLayout(margins=False))
        self.window.new_autorow()
        self.grid_bot = gb = self.window.add(_g.GridLayout(margins=False), alignment=0)
        self.tabs_settings = gb.add(_g.TabArea(autosettings_path=name+'.tabs_settings'))
        self.tabs_data     = gb.add(_g.TabArea(autosettings_path=name+'.tabs_data'), alignment=0)
        
        #################################
        # Top controls
        
        self.button_acquire = gt.add(_g.Button(
            'Acquire', checkable=True,
            tip='Aquire fake Geiger data according to the settings below.',
            signal_toggled = self._button_acquire_toggled,
            style_checked   = 'font-size:20px; color:white; background-color:red',
            style_unchecked = 'font-size:20px; color:None;  background-color:None',
            )).set_width(120)
  
        gt.add(_g.Label('  Counts: ')).set_style('font-size:20px;')
        self.number_counts = gt.add(_g.NumberBox(
            0, 1, bounds=(0,None), int=True,
            )).set_style('font-size:20px').set_width(150)
        
        gt.add(_g.Label('  Time:')).set_style('font-size:20px;')
        self.number_time = gt.add(_g.NumberBox(
            0, 1, bounds=(0,None), siPrefix=True, suffix='s',
            )).set_style('font-size:20px').set_width(150)
        
        self.button_reset = gt.add(_g.Button(
            text='Reset', signal_clicked=self._button_reset_clicked,
            tip='Reset counts and time.')).set_style('font-size:20px;')
        
        #################################
        # Settings
        
        self.tab_settings = ts = self.tabs_settings.add('Settings')
        
        ts.new_autorow()
        self.settings = s = ts.add(_g.TreeDictionary(autosettings_path=name+'.settings')).set_width(290)
        
        s.add_parameter('Source-Detector Distance', 0.01, step=0.001,
                        siPrefix=True, suffix='m', bounds=(1e-3, None), 
                        tip='Distance from the source to the detector.')
        
        
        s.add_parameter('Acquisition Time', 1.0, dec=True, 
                        siPrefix=True, suffix='s', bounds=(1e-9, None),
                        tip='How long to acquire data for.')
        
        s.add_parameter('Iterations', 1, dec=True, bounds=(0,None),
                        tip='How many times to repeat the acquisition. 0 means "keep looping".')
        
        s.add_parameter('Iterations/Completed', 0, readonly=True, 
                        tip='How many acquisitions have been completed.')
        
        s.add_parameter('Iterations/Reset Each Time', True, 
                        tip='Click the reset button at the start of each iteration.')
        
        s.add_parameter('Engine/Rate at 1 mm', 2000.0, bounds=(0, None), 
                        siPrefix=True, suffix='Counts/s',
                        tip='Average counts per second when positioned at 1 mm.')
        
        s.add_parameter('Engine/Time Resolution', 1e-4, 
                        siPrefix=True, suffix='s', dec=True, bounds=(1e-12,None),
                        tip='Time resolution of the detector. Should be small enough\n'
                           +'that only one click happens per time step, but large enough\n'
                           +'that the random number generator will not bottom out.')
        
        s.add_parameter('Engine/Chunk Size', 0.1, 
                        siPrefix=True, suffix='s', dec=True, bounds=(1e-10,None),
                        tip='How long each chunk should be during acquisition.')
        
        s.add_parameter('Engine/Simulate Delay', True, 
                        tip='Whether to pause appropriately during acquisition.')
        
        ###################################
        # Plots
        
        self.tab_raw  = tr = self.tabs_data.add('Raw Data')
        self.plot_raw = tr.add(_g.DataboxPlot('*.raw', autosettings_path=name+'.plot_raw'), alignment=0)
        
        self.tab_log  = tl = self.tabs_data.add('Logger')
        self.plot_log = tl.add(_g.DataboxPlot('*.log', autosettings_path=name+'.plot_log', show_logger=True), alignment=0)
        
        ###################################
        # Start the show!
        
        self.window.show(block)
    
    def _button_reset_clicked(self, *a):
        """
        Reset the time and counts.
        """
        self.number_counts(0)
        self.number_time(0)
        self.plot_raw.clear()
        
    def _button_acquire_toggled(self, *a):
        """
        Someone toggled "Acquire".
        """
        # Let the loop finish itself
        if not self.button_acquire.is_checked(): return
        
        # Shortcut
        s = self.settings
        
        # Loop
        s['Iterations/Completed'] = 0
        while self.button_acquire.is_checked() \
        and  (s['Iterations/Completed'] < s['Iterations'] or s['Iterations'] <= 0):

            # Get a data set
            self.acquire_data()            
            
            s['Iterations/Completed'] += 1
            self.window.process_events()
        
        # Uncheck it.
        self.button_acquire.set_checked(False)

    def acquire_data(self):
        """
        Acquires data and processes / plots it, as per the shown settings.
        """
        # Shortcuts
        s = self.settings
        d = self.plot_raw
        l = self.plot_log
        
        # Get the mean rate using naive 1/r^2 fall off
        rate = s['Engine/Rate at 1 mm'] * (1e-3 / s['Source-Detector Distance'])**2
        dt   = s['Engine/Time Resolution']
        DT   = s['Engine/Chunk Size']
        
        # Get the probability per time step of a tick
        p = rate*dt
        
        # Remaining time to count down
        N = int(_n.round(s['Acquisition Time']/dt))  # Total number of steps
        n = min(int(_n.ceil(DT/dt)), 100000)
        
        # If we're supposed to
        if s['Iterations/Reset Each Time']: self.button_reset.click()
        
        # Acquire in chunks until it's done.
        t0 = _t.time()
        while N > 0 and self.button_acquire.is_checked():
            
            # Get the last time
            if 't' in d.ckeys: t_start = d['t'][-1]+dt
            else:              t_start = dt
            
            # Clear the data
            d.clear()
            s.send_to_databox_header(d)
                        
            # Generate the time data
            d['t']     = _n.linspace(t_start,t_start+(n-1)*dt,n)
            d['Count'] = _n.zeros(n)
            
            # Now get the time bins with a click
            d['Count'][_n.random.rand(n)<p] = 1
            d.plot()
            
            # Update the master numbers
            self.number_counts.increment(len(_n.where(d['Count'] == 1)[0]))
            self.number_time  .increment(n*dt)
            
            # Update remaining time
            N -= n
            
            # Update GUI, then wait for the chunk time minus processing time
            self.window.process_events()
            if s['Engine/Simulate Delay']: self.window.sleep(DT - (_t.time()-t0), 0.005)
            
            # Update t0
            t0 = _t.time()
        
        # All done! Send this info to the logger if we didn't cancel
        if self.button_acquire():
            
            # If we don't have a "last" run number, set it to 0 (incremented later)
            if not 'Run #' in l.ckeys: i = 0
            
            # Otherwise, use the actual last run number
            else: i = l['Run #'][-1]
            
            # Append the data to the logger.
            l.append_row(
                [i+1, s['Source-Detector Distance'], s['Acquisition Time'], self.number_time(), self.number_counts()],
                ['Run #', 'Distance (m)', 'Acquisition (s)', 'Total (s)', 'Counts'])
            l.plot()
            
            
            

if __name__ == '__main__':
    _egg.clear_egg_settings()
    
    self = geiger_simulation()