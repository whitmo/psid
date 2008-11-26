try:
    from paver.virtual import bootstrap
except :
    # minilib does not support bootstrap
    pass
from ConfigParser import ConfigParser as CP
from functools import partial
from paver.defaults import options, Bunch, task, sh, needs
from paver.runtime import debug, call_task
from pkg_resources import working_set, PathMetadata, Distribution, EggMetadata
from setuptools import find_packages
from setuptools.command.easy_install import PthDistributions
import distutils.debug
import os
import pkg_resources
import shutil
import sys
import zipimport

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
    'ZODBMiddleware>=0.1dev'
    ]

setup_deps = [
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
                                     'http://svn.pythonpaste.org/Paste/WebTest/trunk#egg=WebTest'
                                     ],
                   include_package_data=True,
                   zip_safe=False,
                   install_requires = install_requires,
                   entry_points = entry_points
                   )

options(setup=psid_bunch,
        virtualenv=virtualenv)

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
    """Installs pip, easy_installs better behaved younger brother"""
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
    """Installs zc.buildout and buildout recipes for use by other tasks"""
    root = sys.prefix
    pip_path = get_pip_path()

    try:
        import zc.buildout
        import zc.recipe.egg
        import hexagonit.recipe.cmmi
    except ImportError:
        sh(sjoin(sys.executable, pip_path, 'install -r recipes.txt --ignore-installed'))
        add_to_sys_path('hexagonit')
        add_to_sys_path('hexagonit.recipe.cmmi')
        add_to_sys_path('zc')
        add_to_sys_path('zc.buildout')
        add_to_sys_path('zc.recipe.egg')
        import hexagonit.recipe.cmmi
        import zc.buildout
        import zc.recipe.egg


def make_POpts():
    from zc.buildout.buildout import Options, MissingOption
    import zc.buildout
    
    class POpts(Options):

        def __init__(self, buildout, section, data):
            Options.__init__(self, buildout, section, data)
            self.sub_all()

        def sub_all(self):
            for k, v in self._raw.items():
                if '${' in v:
                    self._dosub(k, v)

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
                # only change from original  (no seen)
                v = self.buildout[s[0]].get(s[1], None)
                if v is None:
                    raise MissingOption("Referenced option does not exist:", *s)
                subs.append(v)
            subs.append('')

            return ''.join([''.join(v) for v in zip(value[::2], subs)])
    return POpts

@task
def compose_index():
    """create a simple pypi style index for for this virtualenv"""
    try:
        import compoze
    except ImportError:
        sh(sjoin(sys.executable, get_pip_path(), 'install -i http://dist.repoze.org/simple compoze'))
    dlpath = os.path.join(sys.prefix, 'downloads')
    sh(sjoin('%s/bin/compoze' %sys.prefix, 'fetch --path ', dlpath, ' --fetch-site-packages',
             'index --path', dlpath ))

        
_bo_conf = None
@task
def load_config():
    """load up buildout configuration for use by recipes"""
    global _bo_conf
    _bo_conf = ConfigMap.load('buildout.cfg')

def section_get(section):
    return partial(_bo_conf.parser.get, section)

def section_dict(section, vars=None):
    return dict(_bo_conf.get(section, vars=vars))

@task
@needs(['install_recipes', 'load_config'])
def install_spatialindex():
    """Installs headers and libraries for libspatialindex"""
    name = 'libspatialindex'
    root = sys.prefix
    install_dir = os.path.join(root, 'lib', name)
    comp_dir = install_dir + "__compile__"
    if os.path.exists(comp_dir):
        shutil.rmtree(comp_dir)
    if os.path.exists(install_dir):
        debug("Remove %s if you need to reinstall %s" %(install_dir, name))
    else:
        fake_buildout = create_fake_buildout()
        from hexagonit.recipe.cmmi import Recipe
        spi_opt = section_get('libspatialindex')
        options = dict(url=spi_opt('url'))

        recipe = Recipe(fake_buildout, name, options)
        recipe.options['location']=install_dir
        recipe.options['prefix']=install_dir
        recipe.options['compile-directory']=comp_dir
        
        recipe.install()

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
    fake_buildout = create_fake_buildout()
    ls_path = os.path.join(sys.prefix, 'lib', 'libspatialindex')
    lsl = fake_buildout.setdefault('libspatialindex', dict(location=ls_path))
    rec_klass = pkg_resources.load_entry_point("zc.recipe.egg", 'zc.buildout', 'custom')

    POpts = make_POpts()
    opts = POpts(fake_buildout, 'rtree', section_dict(section))
    recipe = rec_klass(fake_buildout, section, opts)

    sh(get_pip_path() + "install --no-install Rtree")
    rtree_src = os.path.join(sys.prefix, 'build', 'Rtree')
    setup_cfg = os.path.join(rtree_src, 'setup.cfg')

    import setuptools.command.setopt
    setuptools.command.setopt.edit_config(setup_cfg, dict(build_ext=recipe.build_ext))

    sh('cd %s; %s setup.py install' %(rtree_src, sys.executable))

    
def egg_distribution(egg_path):
    if os.path.isdir(egg_path):
        metadata = PathMetadata(egg_path,os.path.join(egg_path,'EGG-INFO'))
    else:
        metadata = EggMetadata(zipimport.zipimporter(egg_path))
    return Distribution.from_filename(egg_path,metadata=metadata)

def update_pth(egg_path):
    spd = get_site_packages_dir()
    easy_install_pth = os.path.join(spd, "easy-install.pth")
    distros = PthDistributions(easy_install_pth)
    distros.add(egg_distribution(egg_path))
    distros.save()


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


