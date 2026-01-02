__version__ = '3.12.1' # Keep this on the first line
# We will now match the first two digits to the spinmob version against 
# which this is tested, and increment the last digit as we make changes.

from setuptools import setup, find_packages

setup(
    name             = 'McPhysics',
    version          = __version__,
    description      = 'Useful tools for the McGill Undergraduate Physics Labs',
    author           = 'Jack Sankey',
    author_email     = 'jack.sankey@gmail.com',
    url              = 'https://github.com/sankeylab/mcphysics',

    # find_packages() handles the code folders with __init__.py
    packages         = find_packages(),

    # This tells setuptools to trust your MANIFEST.in file
    include_package_data = True,
)
