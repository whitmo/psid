from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='psid',
      version=version,
      description="simple spatial index server",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Sean Gillies and Whit Morriss',
      author_email='whit [at] opengeo.org',
      url='',
      license='BSDish',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'PasteDeploy',
          'simplejson',
          'WebOb',
          'WebTest',
          'decorator',
          'PEAK-Rules',
          'selector'
      ],
      test_suite = 'nose.collector',
      entry_points="""
      # -*- Entry points: -*-
      [paste.app_factory]
      main = psid.app:make_app
      """,
      )
