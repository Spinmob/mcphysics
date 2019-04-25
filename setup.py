

version = '1.1.0'



from distutils.core import setup
setup(name           = 'McPhysics',
      version        = version,
      description    = 'Useful tools for the McGill Undergraduate Physics Labs',
      author         = 'Jack Sankey',
      author_email   = 'jack.sankey@gmail.com',
      url            = 'https://github.com/sankeylab/mcphysics',
      packages       = ['mcphysics'],
      package_dir    = {'mcphysics' : '.'}
     )
