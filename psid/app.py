#from selector import pliant, opliant, ByMethod
#from webob import exc, Request, Response
from paste.deploy.config import ConfigMiddleware
from psid import wsgi
from selector import ByMethod
import static
from webob import Response, Request


class RootHandler(ByMethod):

    def index(self, req, start_response):
        environ = req.environ.copy()
        environ['PATH_INFO'] = '/index.html'
        return get_static(req)(environ, start_response)

    def query(self, req, start_response):
        res = Response(content_type='text/javascript; charset=utf8')
        index = res.environ['psid.index']
        

    def GET(self, req, start_response):
        """dispatch for GET conditions"""
        path_seg = self.path_seg = req.path.split("/")

        if not req.queryvars:
            return self.index(req, start_response)

        return self.query(req, start_response)

    def POST(self, request, start_response):
        # add a record
        pass

    def HEAD(self, request, start_response):
        pass


def get_static(req):
    return req.environ['paste.config']['psid.static_app']

def get_static_res(req, start_response):
    app = get_static(req)
    ec = req.environ.copy()
    ec['PATH_INFO'] = "/" + ec['selector.vars']['filename']
    return app(ec, start_response)


class ItemHandler(ByMethod):
    def GET(self, request, start_response):
        pass

    def POST(self, request, start_response):
        pass

    def HEAD(self, request, start_response):
        pass

    def DELETE(self, request, start_response):
        pass

    def PUT(self, request, start_response):
        pass

    
def service_doc(environ, start_response):
    pass

def admin(environ, start_response):
    pass


class IndexMiddleWare(object):
    """Middleware for accessing the rtree index"""

    def __init__(self, application, config):
        self.app = application

    def __call__(self, environ, start_response):
        req = Request(environ)
        resp = req.get_response(self.app)
        return resp(environ, start_response)


def make_app(global_conf, **kw):
    app = wsgi.PSIDSelector(wrap=wsgi.WebObWrapper)
    conf = global_conf.copy()
    conf.update(kw)

    # load up static resources
    res_spec = conf.get('resource', 'psid:resource').split(":")
    magics = [static.StringMagic(**conf)]
    if len(res_spec) == 2:
        pkg, res = res_spec
        static_app = wsgi.shock_wrap(pkg, res, magics=magics)
    else:
        res = res_spec[0]
        static_app = static.Shock(res, magics=magics)

    conf['psid.static_app'] = static_app

    # setup 'routes'
    app.add("/", RootHandler())
    app.add("/static/{filename:segment}", GET=get_static_res)
    app.add("/service-doc", GET=service_doc)
    app.add("/admin", GET=admin)
    app.add("/{uid}", ItemHandler())


    app = ConfigMiddleware(app, conf)
    app = IndexMiddleWare(app, conf)
    return app

