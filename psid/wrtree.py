"""
wgsi middleware for rtree access
"""
from __future__ import with_statement
from paste.wsgilib import catch_errors
import pkg_resources
from rtree import Rtree
import os


class ThreadSafeRtree(Rtree):
    
    def add(id_, coords):
        with threading.RLock():
            Rtree.add(self, id_, coords)

    def delete(id_, coords):
        with threading.RLock():
            Rtree.delete(self, id_, coords)            



class RtreeMiddleWare(object):
    """
    Middleware wrapper for Rtree spatial index
    """
    rtree_factory = ThreadSafeRtree

    def __init__(self, app, base_path, clear_index=False):
        self.app = app

        # in config
        self._base_path = base_path

        if clear_index:
            try:
                os.unlink('%s.dat' % self._basepath)
                os.unlink('%s.idx' % self._basepath)
            except:
                pass

    def __call__(self, environ, start_response):
        environ["psid.rtree"] = self.rtree_factory(self._base_path)
        # use to make transactional?
        def error_callback(exc_info):
            pass
        def ok_callback():
            pass
        return catch_errors(self.app, environ, start_response,
                            error_callback, ok_callback)


def make_rtree_middleware(app, global_conf, base_path=None, clear_index=False):
    if base_path is None:
        base_path = global_conf.get('rtree_basepath')
    if base_path.find(":") >= 0:
        dist, path = base_path.split(':')
        req = pkg_resources.Requirement.parse(dist)
        base_path = pkg_resources.resource_filename(req, path)
            
    return RtreeMiddleWare(app, base_path, clear_index=clear_index)

    
## 
## import threading

## some_rlock = threading.RLock()

## with some_rlock:
##     print "some_rlock is locked while this executes"        
