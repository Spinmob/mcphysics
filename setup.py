__version__ = '1.5.6' # Keep this on the first line



from distutils.core import setup
setup(name           = 'McPhysics',
      version        = __version__,
      description    = 'Useful tools for the McGill Undergraduate Physics Labs',
      author         = 'Jack Sankey',
      author_email   = 'jack.sankey@gmail.com',
      url            = 'https://github.com/sankeylab/mcphysics',

      packages       = [
          'mcphysics',
          'mcphysics.instruments',
          'mcphysics.experiments'],

      package_dir    = {
          'mcphysics' : '.',
          'instruments' : './instruments',
          'experiments' : './experiments'},

      package_data={
          ''  : [
              './setup.py',
              './plot_scripts/*/*',
              './tests/*',
              './tests/data/*'
            ],
          },
      include_package_data=True,
     )
