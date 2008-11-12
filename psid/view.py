from webob import exc

class Handler(object):

    def GET(self):
        return self.forbidden("Not Implemented", *self.wsgi)

    def POST(self):
        return self.forbidden("Not Implemented", *self.wsgi)

    def PUT(self):
        return self.forbidden("Not Implemented", *self.wsgi)

    def DELETE(self):
        return self.forbidden("Not Implemented", *self.wsgi)

    @classmethod
    def on_method(cls, path_seg, req):
        handler = cls(path_seg, req)
        method = getattr(handler, req.method)
        return method(path_seg, req)
    
    def forbidden(self, msg, wsgi):
        return exc.HTTPForbidden(msg)(*wsgi)        


class AdminPage(Handler):
    """Admin page"""


class IndexItem(Handler):
    """Item Handling"""


class ServiceIndex(Handler):
    """default page"""


class ServiceDocument(Handler):
    """service document"""


class Query(Handler):
    "handles queries"
