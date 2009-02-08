try:
    from paver.virtual import bootstrap
except :
    # minilib does not support bootstrap
    pass
from pkg_resources import working_set
from paver.defaults import options, Bunch, task, sh, needs
from paver.runtime import call_task
from setuptools import find_packages
import distutils.debug
import os
import shutil
import sys

# placeholders: we will populate this after loading with pip
steamroller = None
pip = None
rolluts = None
rollbo = None
pip_path = os.path.join(sys.prefix, 'bin', 'pip')
easy_install_path = os.path.join(sys.prefix, 'bin', 'easy_install')
distutils.debug.DEBUG = True

__version__ = '0.1'

README= ''
CHANGES=''

entry_points = \
"""
[paste.app_factory]
main = psid.app:make_app
[paste.filter_app_factory]
rtree = psid.wrtree:make_rtree_middleware
tm_rtree = psid.wrtree:make_tmrtree_middleware
rtree_index = psid.wrtree:make_rtree_index_component
[psid.reverse_index]
default=psid.wrtree:zodb_rindex_handler
zodb=psid.wrtree:zodb_rindex_handler
[zodb_init]
default=psid.wrtree:zodb_init
"""

install_requires=[
    'PasteDeploy',
    'PasteScript',
    'WebOb',
    'ZODB3',
    'resolver',
    'decorator',
    'repoze.tm2',
    'selector',
    'simplejson',
    'static',
    'steamroller',
    'ZODBMiddleware>=0.1dev'
    ]

setup_deps = [
    'steamroller',
    "zc.buildout",
    "zc.recipe.egg",
    "hexagonit.recipe.cmmi",
    'nose',
    'pip',
    'virtualenv',
    'setuptools>0.6c8'
    ]

virtualenv = Bunch(
        script_name="psid_env.py",
        packages_to_install=install_requires + setup_deps,
        ) 


psid_bunch = Bunch(name='psid',
                   version=__version__,
                   description='install psid and dependencies',
                   long_description="",
                   classifiers=["Development Status :: 3 - Alpha",
                                "Intended Audience :: Developers",
                                "Programming Language :: Python",
                                "Topic :: Internet :: WWW/HTTP",
                                "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
                                "Topic :: Internet :: WWW/HTTP :: WSGI",
                                "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
                                ],
                   keywords='',
                   author="Sean Gillies and Whit Morriss",
                   author_email="psid@list.opengeo.org",
                   url="http://psid.opengeo.org",
                   license="BSD",
                   test_requires=["WebTest>=1.1.1dev",
                                  "nose"
                                  ],
                   test_suite='nose.collector',
                   packages=find_packages(),
                   dependency_links=['http://dist.repoze.org/lemonade/dev/simple',
                                     'https://svn.openplans.org/svn/ZODBMiddleware/trunk#egg=ZODBMiddleware-0.1dev',
                                     'http://svn.pythonpaste.org/Paste/WebTest/trunk#egg=WebTest',
                                     'http://is.gd/iDw4#egg=steamroller'
                                     ],
                   include_package_data=True,
                   zip_safe=False,
                   install_requires = install_requires,
                   entry_points = entry_points
                   )

options(setup=psid_bunch,
        virtualenv=virtualenv)
        
def sjoin(*args):
    return " ".join(args)

@task
def install_pip():
    """Installs pip, easy_installs better behaved younger brother"""
    root = sys.prefix
    global pip
    try:
        import pip
    except ImportError:
        sh(easy_install_path+' pip')
        site_packages_dir = os.path.dirname(os.__file__) +'/site-packages/'
        for path in os.listdir(site_packages_dir):
            if path.startswith('pip'):
                sys.path.append(site_packages_dir+path)
                working_set.add_entry(site_packages_dir+path)
                return
    import pip


@task
@needs('install_pip')
def bootstrap_steamroller():
    global steamroller, pip_path, rolluts, rollbo
    try:
        import steamroller
    except ImportError:
        sh(sjoin(sys.executable, pip_path, 'install -r roller.txt'))
    import steamroller #@@??
    import steamroller.utils as rolluts
    import steamroller.bo as rollbo

@task
@needs('bootstrap_steamroller')
def install_recipes():
    """Installs zc.buildout and buildout recipes for use by other tasks"""
    root = sys.prefix
    try:
        import zc.buildout
        import zc.recipe.egg
        import hexagonit.recipe.cmmi
    except ImportError:
        sh(sjoin(sys.executable, pip_path, 'install -r recipes.txt --ignore-installed'))
        rolluts.add_to_sys_path('hexagonit')
        rolluts.add_to_sys_path('hexagonit.recipe.cmmi')
        rolluts.add_to_sys_path('zc')
        rolluts.add_to_sys_path('zc.buildout')
        rolluts.add_to_sys_path('zc.recipe.egg')
        import hexagonit.recipe.cmmi
        import zc.buildout
        import zc.recipe.egg

@task
@needs('bootstrap_steamroller')
def load_bo_conf():
    pass

@task
def compose_index():
    """create a simple pypi style index for for this virtualenv"""
    try:
        import compoze
    except ImportError:
        sh(sjoin(sys.executable, pip_path, 'install -i http://dist.repoze.org/simple compoze'))
    dlpath = os.path.join(sys.prefix, 'downloads')
    sh(sjoin('%s/bin/compoze' %sys.prefix, 'fetch --path ', dlpath, ' --fetch-site-packages',
             'index --path', dlpath ))

_buildout = None
@task
def load_config():
    """load up buildout configuration for use by recipes"""
    global _buildout
    _buildout = rollbo.BuildoutCfg.loadfn('buildout.cfg')

@task
@needs(['install_recipes', 'load_config'])
def install_spatialindex():
    """Installs headers and libraries for libspatialindex"""
    name = 'libspatialindex'
    rollbo.hexagonit_cmmi(name, _buildout)

@task
def de_env():
    """Delete 'bin' and 'lib'. Not reversible"""
    shutil.rmtree(os.path.join(sys.prefix, 'bin'))
    shutil.rmtree(os.path.join(sys.prefix, 'lib'))

# fix logging to understand buildout
@task
@needs('install_spatialindex')
def install_rtree_egg():
    """Install Rtree distribution according to arguments in buildout.cfg"""
    # rewrite to not use buildout
    section = 'rtree'
    def set_libspatial_path(fake_buildout):
        import sys
        ls_path = os.path.join(sys.prefix, 'lib', 'libspatialindex') 
        lsl = fake_buildout.setdefault('libspatialindex', dict(location=ls_path)) 
        return fake_buildout
    try:
        rollbo.custom_egg_brute_install("rtree", _buildout, mod_buildout=set_libspatial_path)
    except :
        raise
        import pdb, sys; pdb.post_mortem(sys.exc_info()[2])

@task
@needs('install_rtree_egg')
def install():
    """install psid w/ all dependencies"""
    call_task("setuptools.command.install")

@task
@needs('install_rtree_egg')
def develop():
    """Install all dependencies and develop install psid"""
    call_task("setuptools.command.develop")    

@task
@needs(['generate_setup', 'minilib', 'setuptools.command.sdist'])
def sdist():
    """create a source distribution"""
    call_task("setuptools.command.sdist")    

@task
def bdist_egg():
    """create an egg distribution"""
    call_task("setuptools.command.bdist_egg")



