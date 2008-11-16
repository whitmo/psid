======
 PSID
======

'PSID spatially indexes data/documents'

 psid provides a general wsgi application for indexing points.

Requirements
============

  * Python 2.5 or greater

  * Currently only tested on *ix platforms (might work elsewhere):

    - MacOSX 10.5

Installation
============

 Psid is designed by default to install into virtualenv based
 environments. See 'virtualenv and sid' below for more information.

 In most cases all that is required is a standard
 python install::

  python setup.py install

 This will install the C libs for libspatialindex and the Rtree
 distribution required by PSID as well as several other dependencies.
 see docs/installation.txt


psid and virtualenv
-------------------

Psid comes with a special virtualenv bootstrap that
 creates a virtualenv with most of Psid's dependencies installed
 (eventually this will grow to have psid completely installed)::

  python psid_env.py mypsidenv
  cd mysidenv
  . bin/activate



