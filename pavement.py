from paver.defaults import options, Bunch, task, sh, needs
from paver.runtime import debug, call_task
from pkg_resources import working_set
try:
    from paver.virtual import bootstrap
except :
    # minilib does not support bootstrap
    pass
from ConfigParser import ConfigParser as CP
import pkg_resources
from functools import partial
from setuptools import setup, find_packages
import os
import shutil, time, tempfile
import sys

__version__ = '0.1'

README= ''
CHANGES=''

install_requires=[
    'PasteDeploy',
    'simplejson',
    'WebOb',
    'WebTest',
    'decorator',
    'selector',
    'static'
    ]


virtualenv = Bunch(
        script_name="psid_env.py",
        packages_to_install=install_requires + ['nose','pip'],
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
                   test_suite='nose.collector',
                   packages=find_packages(),
                   include_package_data=True,
                   zip_safe=False,
                   install_requires = install_requires,
                   entry_points = """\
                   [paste.app_factory]
                   main = psid.app:make_app
                   """
                   )

options(setup=psid_bunch,
        virtualenv=virtualenv)

import logging
logger = logging.getLogger('zc.buildout.easy_install')

def create_fake_buildout():
    root = sys.prefix
    fake_buildout = dict(buildout=dict())
    fake_buildout['buildout']['parts-directory'] = root
    fake_buildout['buildout']['directory'] = root
    fake_buildout['buildout']['offline'] = 'false'

    # FAKE OUT buildout python abstraction
    fake_buildout['buildout']['python'] = 'paver_python'
    fake_buildout.setdefault('paver_python', dict(executable=sys.executable))
    fake_buildout['buildout']['eggs-directory'] = get_site_packages_dir()
    fake_buildout['buildout']['develop-eggs-directory'] = get_site_packages_dir()
    return fake_buildout

def get_site_packages_dir():
    return os.path.dirname(os.__file__) +'/site-packages/'

def get_easy_install_path():
    return os.path.join(sys.prefix, 'bin', 'easy_install')

def get_pip_path():
    return os.path.join(sys.prefix, 'bin', 'pip')

def add_to_sys_path(package):
    site_packages_dir = get_site_packages_dir()
    for path in os.listdir(site_packages_dir):
        if path.startswith(package):
            sys.path.append(site_packages_dir+path)
            working_set.add_entry(site_packages_dir+path)
            return

@task
def install_pip():
    root = sys.prefix
    easy_install_path = get_easy_install_path()
    try:
        import pip
    except ImportError:
        sh(easy_install_path+' pip')
        add_to_sys_path('pip')
        import pip

def sjoin(*args):
    return " ".join(args)



@task
@needs('install_pip')
def install_recipes():
    root = sys.prefix
    pip_path = get_pip_path()

    try:
        import zc.buildout
        import zc.recipe.egg
        import hexagonit.recipe.cmmi
    except ImportError:
        sh(sjoin(sys.executable, pip_path, 'install -r recipes.txt --ignore-installed'))
        add_to_sys_path('zc.buildout')
        add_to_sys_path('zc.recipe.egg')
        add_to_sys_path('hexagonit.recipe.cmmi')
        import zc.buildout
        import zc.recipe.egg
        import hexagonit.recipe.cmmi


_bo_conf = None
@task
def load_config():
    global _bo_conf
    _bo_conf = ConfigMap.load('buildout.cfg')

def section_get(section):
    return partial(_bo_conf.parser.get, section)

def section_dict(section, vars=None):
    return dict(_bo_conf.get(section, vars=vars))

@task
@needs(['install_recipes', 'load_config'])
def install_spatialindex():
    name = 'libspatialindex'
    root = sys.prefix
    install = os.path.join(root, name)
    comp_dir = install + "__compile__"
    if os.path.exists(comp_dir):
        shutil.rmtree(comp_dir)
    if os.path.exists(install):
        debug("Remove %s if you need to reinstall %s" %(install, name))
    else:
        fake_buildout = create_fake_buildout()
        from hexagonit.recipe.cmmi import Recipe
        spi_opt = section_get('libspatialindex')
        options = dict(url=spi_opt('url'))
        recipe = Recipe(fake_buildout, name, options)
        recipe.install()
        
from zc.buildout.buildout import Options, MissingOption

import zc.buildout
import re

class POpts(Options):

    def __init__(self, buildout, section, data):
        Options.__init__(self, buildout, section, data)
        self.sub_all()
        
    def sub_all(self):
        for k, v in self._raw.items():
            if '${' in v:
                self._dosub(k, v)

    _template_split = re.compile('([$]{[^}]*})').split
    _simple = re.compile('[-a-zA-Z0-9 ._]+$').match
    _valid = re.compile('\${[-a-zA-Z0-9 ._]+:[-a-zA-Z0-9 ._]+}$').match
    def _sub(self, template, seen):
        value = self._template_split(template)
        subs = []
        for ref in value[1::2]:
            s = tuple(ref[2:-1].split(':'))
            if not self._valid(ref):
                if len(s) < 2:
                    raise zc.buildout.UserError("The substitution, %s,\n"
                                                "doesn't contain a colon."
                                                % ref)
                if len(s) > 2:
                    raise zc.buildout.UserError("The substitution, %s,\n"
                                                "has too many colons."
                                                % ref)
                if not self._simple(s[0]):
                    raise zc.buildout.UserError(
                        "The section name in substitution, %s,\n"
                        "has invalid characters."
                        % ref)
                if not self._simple(s[1]):
                    raise zc.buildout.UserError(
                        "The option name in substitution, %s,\n"
                        "has invalid characters."
                        % ref)
                
            v = self.buildout[s[0]].get(s[1], None)
            if v is None:
                raise MissingOption("Referenced option does not exist:", *s)
            subs.append(v)
        subs.append('')

        return ''.join([''.join(v) for v in zip(value[::2], subs)])                

# fix logging to understand buildout
                
@task
@needs('install_spatialindex')
def install_rtree_egg():
    section = 'rtree'
    fake_buildout = create_fake_buildout()
    ls_path = os.path.join(sys.prefix, 'libspatialindex')
    lsl = fake_buildout.setdefault('libspatialindex', dict(location=ls_path))
    rec_ep = pkg_resources.load_entry_point("zc.recipe.egg", 'zc.buildout', 'custom')
    opts = POpts(fake_buildout, 'rtree', section_dict(section))
    recipe = rec_ep(fake_buildout, section, opts)
    recipe.install()

    # this should put it on the path
    sh(get_easy_install_path() + ' Rtree')

@task
@needs('install_rtree_egg')
def install():
    call_task("setuptools.command.install")

@task
@needs('install_rtree_egg')
def develop():
    call_task("setuptools.command.develop")    

@task
@needs(['generate_setup', 'minilib', 'setuptools.command.sdist'])
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass

@task
def bdist_egg():
    """Overrides sdist to make sure that our setup.py is generated."""
    call_task("setuptools.command.install")


class ConfigMap(object):

    def __init__(self, parser):
        self.parser = parser
        self.sects = parser.sections()

    def __iter__(self):
        for sname in self.sects:
            yield sname
            
    def __getitem__(self, idx):
        return dict(self.get(idx))

    def get(self, idx, vars=None):
        return self.parser.items(idx, vars=vars)

    @classmethod
    def load(cls, fname):
        parser = CP()
        parser.read(fname)
        return cls(parser)


