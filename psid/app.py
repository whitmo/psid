#from selector import pliant, opliant, ByMethod
#from webob import exc, Request, Response
from paste.deploy.config import ConfigMiddleware
from psid import wsgi
from selector import ByMethod
from webob import Response
import simplejson
import static


class BaseHandler(ByMethod):

    def rtree(self, req):
        return req.environ['psid.rtree']

    def rtree_raw(self, req):
        return req.environ['psid.rtree_raw']
    



class RootHandler(BaseHandler):

    def index(self, req, start_response):
        environ = req.environ.copy()
        environ['PATH_INFO'] = '/index.html'
        return get_static(req)(environ, start_response)

    def query(self, req, start_response):
        res = Response(content_type='application/json')
        index = self.rtree(req)

        hits = index.intersection(tuple(GET_bounds(req)))
        res.body = simplejson.dumps(hits)
        return res

    def GET(self, req, start_response):
        """dispatch for GET conditions"""
        path_seg = self.path_seg = req.path.split("/")

        if not req.GET:
            return self.index(req, start_response)

        return self.query(req, start_response)

    def POST(self, request, start_response):
        json = simplejson.loads(request.body)
        res = Response()
        urls = []

        if json:
            urls.extend(self.add(json, request))
        else:
            res.status = 400
            return res

        if len(urls) == 1:
            res.headers['Location'] = urls[0]
            res.write(urls.pop())
        else:
            for url in urls:
                res.write(url)
        return res
        
    def add(self, json, req):
        if isinstance(json, dict):
            id_ = json['id']
            self.rtree(req)[id_]=tuple(json['bbox'])
            return ["/%s" %json['id']]
        else:
            assert isinstance(json, list), "POST must be an Array or an Object"
            urls = []
            for item in json:
                self.rtree().add(json['id'], tuple(json['bbox']))
                urls.append("/%s" %json['id'])
            return urls
        
    def HEAD(self, request, start_response):
        pass


def get_static(req):
    return req.environ['paste.config']['psid.static_app']

def get_static_res(req, start_response):
    app = get_static(req)
    ec = req.environ.copy()
    ec['PATH_INFO'] = "/" + ec['selector.vars']['filename']
    return app(ec, start_response)


class ItemHandler(BaseHandler):

    def get_uid(self, request):
        """
        """
        uid = request.environ['selector.vars']['uid']
        try:
            # attempt to coerce uid to int
            uid = int(uid)
        except ValueError:
            pass
        return uid
    
    def GET(self, request, start_response):
        res = Response(content_type='application/json')
        index = self.rtree(request)
        uid = self.get_uid(request)
        bounds = index.get(uid)
        if bounds is None:
            res.status_int = 404
            return res
        res.body = simplejson.dumps(dict(id=uid, bbox=bounds))
        return res

    def POST(self, request, start_response):
        raise NotImplementedError

    def HEAD(self, request, start_response):
        raise NotImplementedError

    def DELETE(self, request, start_response):
        uid = request.environ['selector.vars']['uid']
        res = Response(content_type='application/json')
        uid = self.get_uid(request)
        if self.rtree(request).get(uid):
            del self.rtree(request)[uid]
        else:
            res.status_int = 404
        return res

    def PUT(self, request, start_response):
        pass

    
def service_doc(request, start_response):
    static = get_static(request)
    request.environ['PATH_INFO'] = '/service-doc.html'
    return static(request.environ, start_response)

def admin(req, start_response):
    return Response()

def GET_bounds(req, bounds_params=('minx', 'miny', 'maxx', 'maxy' )):
    # improve error output
    try:
        bounds = [float(req.GET.get(param)) for param in bounds_params]
    except IndexError, e:
        raise
    except ValueError, e:
        raise
    return bounds

def nearest(req, start_response):
    bounds = GET_bounds(req)
    howmany = req.GET.get('n', 1)
    rtree = req.environ['psid.rtree']
    res = Response(content_type='application/json')
    hits = rtree.nearest(tuple(bounds), int(howmany))
    res.body = simplejson.dumps(hits)
    return res

def make_whitstyle_api(conf):
    app = wsgi.PSIDSelector(wrap=wsgi.WebObWrapper)

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
    app.add("/nearest", GET=nearest)
    app.add("/{uid}", ItemHandler())

    return app

def make_app(global_conf, **kw):
    conf = global_conf.copy()
    conf.update(kw)

    # configure by entrypoint
    app = make_whitstyle_api(conf)
    app = ConfigMiddleware(app, conf)
    return app


