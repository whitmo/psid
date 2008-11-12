from paste.deploy.config import ConfigMiddleware
#from webob import exc, Request, Response
from webob import Request, exc
from psid import view
from selector import ByMethod
#from selector import pliant, opliant, ByMethod
from psid import wsgi

#from peak.rules import abstract, when, around, before, after
from peak.rules import abstract, when


class SpatialIndexService(object):
    content_type = 'text/javascript; charset=utf8'

    b_dispatch = dict(admin=view.AdminPage,
                     service=view.ServiceDocument,
                     _item_=view.IndexItem,
                     _index_=view.ServiceIndex,
                     _query_=view.Query)

    def __init__(self):
        pass

    @abstract()
    def dispatch_path(self, req, wsgi):
        """dispatch on path"""

    @abstract()
    def GET(self, req, (environ, start_response)):
        """dispatch for GET conditions"""

    @abstract()
    def POST(self, req, (environ, start_response)):
        """POST methods"""        

    @when(GET, "not len(self.normed_seg) and not req.queryvars")
    def index(self, req, wsgi):
        return self._dispatch['_index_'](req, wsgi)

    @when(GET,"not len(self.normed_seg) and req.queryvars")
    def query(self, req, wsgi):
        return self.unused("Do query", wsgi)

    @when(GET, "len(self.normed_seg) > 0")
    def get_item(self, req, wsgi):
        pass

    def PUT(self, req, (environ, start_response)):
        """PUT methods"""
        if not self.normed_seg:
            return exc.HTTPForbidden("HTTP method '%s' is not allow" %req.method)(
                environ, start_response)
        
    def DELETE(self, req, (environ, start_response)):
        """DELETE methods"""
        if not self.normed_seg:
            return exc.HTTPForbidden("HTTP method '%s' is not allow" %req.method)(
                environ, start_response)


    
    def __call__(self, environ, start_response):
        req = Request(environ)
        path_seg = self.path_seg = req.path.split("/")
        self.normed_seg = [x for x in path_seg if x]
        func = getattr(self, req.method, None)
        if func is None:
            return exc.HTTPForbidden("HTTP method '%s' is not allow" %req.method)(
                environ, start_response)
        res = func(req, (environ, start_response))
        if isinstance(res, list):
            return res
        return res(environ, start_response)


class RootHandler(ByMethod):
    def GET(self, request, start_response):
        pass

    def POST(self, request, start_response):
        pass

    def HEAD(self, request, start_response):
        pass


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
    app.add("/", RootHandler())
    app.add("/service-doc", GET=service_doc)
    app.add("/admin", GET=admin)
    app.add("/{uid}", ItemHandler())
    
    # Here we merge all the keys into one configuration
    # dictionary; you don't have to do this, but this
    # can be convenient later to add ad hoc configuration:
    conf = global_conf.copy()
    conf.update(kw)
    app = ConfigMiddleware(app, conf)
    return app
