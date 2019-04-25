import os        as _os
import numpy     as _n
import spinmob   as _s
import mcphysics as _m
import unittest  as _ut

# Globals for monkeywork on the command line
a = b = c = d = x = None

class Test_errthing(_ut.TestCase):
    """
    Test class for mcphysics library.
    """

    def path(self, filename):
        """
        Assembles a path to a file.
        """
        return _os.path.join(self.data_path, filename)

    def setUp(self):
        self.data_path = _os.path.join(_os.path.dirname(_m.__file__), '_tests', 'data')
        return
    
    def tearDown(self):
        return

    def test_data(self):
        
        d = _m.data.load_chn(self.path('signal.Chn'))
        self.assertEqual(len(d), 2)
        self.assertEqual(len(d[1]), 1024)

        ds = _m.data.load_chns([self.path('signal.Chn'), self.path('background.Chn')])
        self.assertEqual(len(ds), 2)
        self.assertEqual(len(ds[1]), 2)
    
        _m.data.plot_chn_files(paths=[self.path('signal.Chn'), self.path('background.Chn')])
    
        image = _m.data.load_image(self.path('image.jpg'))
        self.assertEqual(image.shape, (612, 816, 3))
        
        images = _m.data.load_images([self.path('image.jpg')])
        self.assertEqual(_n.shape(images), (1,612,816,3))
    
    
    def test_functions(self):
        
        _s.plot.xy.function(['em_gaussian(x,1,2)', 'voigt(x,2,1)', 'erfcx(x)', 'reduced_chi2(x,10)'], 
                             1e-6,5,1000,g=_m.functions.__dict__)
    
    def test_instruments(self):
        global a, c
        
        a = _m.instruments.sillyscope(block=True)
        c = _m.instruments.keithley_dmm(block=True)
    
    def test_playground(self):
        global b
        
        b = _m.playground.fitting_statistics_demo(block=True)
        _m.playground.plot_and_integrate_reduced_chi2()
    
if __name__ == "__main__":
    _ut.main()
