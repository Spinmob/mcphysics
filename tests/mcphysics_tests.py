import os        as _os
import numpy     as _n
import spinmob   as _s
import mcphysics as _m
import unittest  as _ut
import shutil    as _sh

# Globals for monkeywork on the command line
a = b = c = d = e = x = None

if _os.path.exists('egg_settings'): _sh.rmtree('egg_settings')

# Path to the data folder
data_path = _os.path.join(_os.path.dirname(_m.__file__), 'tests', 'data')
def path(filename):
    """
    Assembles a path to a particular file.
    """
    return _os.path.join(data_path, filename)


class errthing(_ut.TestCase):
    """
    Test class for mcphysics library.
    """

    def setUp(self):
        return

    def tearDown(self):
        return

    def test_check_installation(self): _m.check_installation()

    def test_data_chn(self):
        global d

        d = _m.data.load_chn(path('signal.Chn'))
        self.assertEqual(len(d), 2)
        self.assertEqual(len(d[1]), 1024)

        ds = _m.data.load_chns([path('signal.Chn'), path('background.Chn')])
        self.assertEqual(len(ds), 2)
        self.assertEqual(len(ds[1]), 2)

        ds = _m.data.convert_chn_to_csv([path('signal.Chn'),path('background.Chn')], '')
        d = _s.data.load('signal.csv')
        self.assertEqual(d.h('start')['month'], 9)

        # Clean up
        print()
        for d in ds:
            print('Removing '+d.path)
            _os.remove(d.path)

        _s.pylab.figure(1)
        _m.data.plot_chns(paths=[path('signal.Chn'), path('background.Chn')])


    def test_data_images(self):

        image = _m.data.load_image(path('image.jpg'))
        self.assertEqual(image.shape, (612, 816, 3))

        images = _m.data.load_images([path('image.jpg')])
        self.assertEqual(_n.shape(images), (1,612,816,3))




    def test_functions(self):

        _s.pylab.figure(2)
        _s.plot.xy.function(['em_gaussian(x,1,2)', 'voigt(x,2,1)', 'erfcx(x)', 'reduced_chi2(x,10)'],
                             1e-6,5,1000,g=_m.functions.__dict__)

    def test_instruments_adalm2000(self):        _m.instruments.adalm2000(block=True)
    def test_instruments_sillyscope(self):       _m.instruments.sillyscope(block=True)
    def test_instruments_keithley_dmm(self):     _m.instruments.keithley_dmm(block=True)
    def test_instruments_auber_syl53x2p(self):   _m.instruments.auber_syl53x2p(block=True)
    def test_instruments_soundcard(self):        _m.instruments.soundcard(block=True)

    def test_experiments_alpha_arduino(self):    _m.experiments.alpha.arduino(block=True)
    def test_experiments_drum_motors_api(self):  _m.experiments.drum.motors_api('Simulation', 'circle')

    def test_playground(self):
        global b

        b = _m.playground.fitting_statistics_demo(block=True)
        _m.playground.plot_and_integrate_reduced_chi2()
        _m.playground.geiger_simulation(block=True)

if __name__ == "__main__":
    _ut.main()
    #_ut.main(defaultTest='errthing.test_data_chn')
