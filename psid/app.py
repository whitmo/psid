#from selector import pliant, opliant, ByMethod
#from webob import exc, Request, Response
from paste.deploy.config import ConfigMiddleware
from psid import view
from psid import wsgi
from selector import ByMethod
import static
from webob import Request, exc


class RootHandler(ByMethod):

    def index(self, req, start_response):
        environ = req.environ.copy()
        environ['PATH_INFO'] = '/index.html'
        return get_static(req)(environ, start_response)

    def GET(self, req, start_response):
        """dispatch for GET conditions"""
        path_seg = self.path_seg = req.path.split("/")

        if not req.queryvars:
            return self.index(req, start_response)

        return # query

    def POST(self, request, start_response):
        # add a record
        pass

    def HEAD(self, request, start_response):
        pass

def get_static(req):
    return req.environ['paste.config']['psid.static_app']

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


def make_app(global_conf, **kw):
    app = wsgi.PSIDSelector(wrap=wsgi.WebObYaro)

##     import tryme
##     app.add('/{}/{}/foo/{bar}/{}', GET=tryme.viewenv)
##     app.add('/{}/{}/bar/{bar}/{}', GET=pliant(tryme.viewenv))
##     app.add('/{}/{}/baz/{bar}/{}', GET=tryme.Viewer())

    conf = global_conf.copy()
    conf.update(kw)

    # load up static resources
    res_spec = conf['resource'].split(":")
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
    app.add("/service-doc", GET=service_doc)
    app.add("/admin", GET=admin)
    app.add("/{uid}", ItemHandler())
    

    app = ConfigMiddleware(app, conf)
    return app

## class SpatialIndexService(object):
##     content_type = 'text/javascript; charset=utf8'

##     b_dispatch = dict(admin=view.AdminPage,
##                      service=view.ServiceDocument,
##                      _item_=view.IndexItem,
##                      _index_=view.ServiceIndex,
##                      _query_=view.Query)

##     def __init__(self):
##         pass


##     def POST(self, req, (environ, start_response)):
##         """POST methods"""        



##     def PUT(self, req, (environ, start_response)):
##         """PUT methods"""
##         if not self.normed_seg:
##             return exc.HTTPForbidden("HTTP method '%s' is not allow" %req.method)(
##                 environ, start_response)
        
##     def DELETE(self, req, (environ, start_response)):
##         """DELETE methods"""
##         if not self.normed_seg:
##             return exc.HTTPForbidden("HTTP method '%s' is not allow" %req.method)(
##                 environ, start_response)


    
##     def __call__(self, environ, start_response):
##         req = Request(environ)
##         path_seg = self.path_seg = req.path.split("/")
##         self.normed_seg = [x for x in path_seg if x]
##         func = getattr(self, req.method, None)
##         if func is None:
##             return exc.HTTPForbidden("HTTP method '%s' is not allow" %req.method)(
##                 environ, start_response)
##         res = func(req, (environ, start_response))
##         if isinstance(res, list):
##             return res
##         return res(environ, start_response)
