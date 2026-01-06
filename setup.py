__version__ = '3.13.1' # Keep this on the first line
# We will now match the first two digits to the spinmob version against 
# which this is tested, and increment the last digit as we make changes.

from setuptools import setup

setup(
    name             = 'McPhysics',
    version          = __version__,
    description      = 'Useful tools for the McGill Undergraduate Physics Labs',
    author           = 'Jack Sankey',
    author_email     = 'jack.sankey@gmail.com',
    url              = 'https://github.com/sankeylab/mcphysics',

    # 1. Manually define the packages again since find_packages() failed 
    # due to the root-level (flat) structure.
    packages         = ['mcphysics', 'mcphysics.instruments', 'mcphysics.experiments'],

    # 2. Map the package name to the current directory ('.')
    package_dir      = {'mcphysics': '.'},

    include_package_data = True,

    install_requires = [
        'imageio',
    ]
)