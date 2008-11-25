"""
wgsi middleware for rtree access
"""
from __future__ import with_statement
from functools import partial
from paste.deploy.config import ConfigMiddleware
from paste.wsgilib import catch_errors
from rtree import Rtree
import os
import pkg_resources
import threading
import transaction


class ThreadSafeRtree(Rtree):
    
    def add(self, id_, coords):
        with threading.RLock():
            Rtree.add(self, id_, coords)

    def delete(self, id_, coords):
        with threading.RLock():
            Rtree.delete(self, id_, coords)            


class RtreeDataManager(object):

    transaction_manager = None

    def __init__(self, rtree):
        self.rtree = rtree
        self.add = {}
        self.delete = {}

    def add(self, id_, bounds):
        self.add[id_]=bounds

    def delete(self, id_, bounds):
        self.delete[id_]=bounds        

    def commit(self, transaction):
        for id_, bounds in self.add.items():
            self.rtree.add(id_, bounds)
        for id_, bounds in self.delete.items():
            self.rtree.delete(id_, bounds)            

    def abort(self, transaction):
        pass

    def tpc_begin(self, transaction):
        pass

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        pass

    def tpc_abort(self, transaction):
        pass
    

class RtreeMiddleWare(object):
    """
    Middleware wrapper for Rtree spatial index
    """
    rtree_factory = ThreadSafeRtree

    def __init__(self, app, base_path, clear_index=False):
        self.app = app
        self._base_path = base_path

        if clear_index:
            try:
                os.unlink('%s.dat' % self.path)
                os.unlink('%s.idx' % self.path)
            except:
                pass

    @property
    def path(self):
        return os.path.join(self._base_path, 'rtree')

    def __call__(self, environ, start_response):
        rtree = environ["psid.rtree"] = self.rtree_factory(self.path)
        
        # debugging
        def error_callback(exc_info):
            pass
        def ok_callback():
            pass
        return catch_errors(self.app, environ, start_response,
                            error_callback, ok_callback)


class TMRtreeMiddleWare(RtreeMiddleWare):
    """
    An implementation of Rtree persistence w/ transaction awareness 
    """
    data_manager = RtreeDataManager
    def __call__(self, environ, start_response):
        rtree = environ["psid.rtree"] = self.rtree_factory(self.path)
        dm = RtreeDataManager(rtree)

        # our add and delete hooks
        environ["psid.rtree.add"] = dm.add
        environ["psid.rtree.add"] = dm.delete

        # join rtree to transaction
        import transaction
        t = transaction.get()
        t.join(dm)
        
        # for debugging remove
        def error_callback(exc_info):
            pass
        def ok_callback():
            pass
        return catch_errors(self.app, environ, start_response,
                            error_callback, ok_callback)


def make_rtree_middleware(app, global_conf, base_path=None, clear_index=False, mw_class=RtreeMiddleWare, **kw):
    conf = global_conf.copy()
    conf.update(kw)
    clear_index = global_conf.get('clear_index', clear_index)

    if base_path is None:
        base_path = conf.get('data_path')

    if base_path.find(":") >= 0:
        dist, path = base_path.split(':')
        req = pkg_resources.Requirement.parse(dist)
        base_path = pkg_resources.resource_filename(req, path)
    return mw_class(app, base_path, clear_index=clear_index)

make_tmrtree_middleware=partial(make_rtree_middleware, mw_class=TMRtreeMiddleWare)


