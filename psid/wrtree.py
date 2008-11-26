"""
wgsi middleware for rtree access
"""
from __future__ import with_statement

from UserDict import DictMixin
from functools import partial
from paste.deploy.config import ConfigMiddleware
from paste.wsgilib import catch_errors
from persistent.mapping import PersistentMapping
from rtree import Rtree
import os
import pkg_resources
import resolver
import threading
import transaction

STORE_ID = "psid.reverse_index"


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
        self._add = {}
        self._delete = {}

    def add(self, id_, bounds):
        self._add[id_]=bounds

    def delete(self, id_, bounds):
        self._delete[id_]=bounds        

    def commit(self, transaction):
        for id_, bounds in self._add.items():
            self.rtree.add(id_, bounds)

        for id_, bounds in self._delete.items():
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
    
    def sortKey(self):
        return id(self)


class RtreeWrapper(object):
    """
    wrapper for Rtree spatial index
    """
    rtree_factory = ThreadSafeRtree

    def __init__(self, app, base_path, clear_index=False):
        self.app = app
        self._base_path = base_path

        self.rtree = self.rtree_factory(self.path)
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
        rtree = environ["psid.rtree"] = self.rtree
        
        # debugging
        def error_callback(exc_info):
            pass
        def ok_callback():
            pass
        return catch_errors(self.app, environ, start_response,
                            error_callback, ok_callback)


class TMRtreeWrapper(RtreeWrapper):
    """
    An implementation of Rtree persistence w/ transaction awareness 
    """
    data_manager_class = RtreeDataManager
    dm = None
    
    def _init_datamanager(self, environ):
        environ["psid.rtree_raw"] = self.rtree
        self.dm = self.data_manager_class(self.rtree)

        import transaction 
        t = transaction.get()
        t.join(self.dm)
        return self.dm
        
    def __call__(self, environ, start_response):
        dm = self._init_datamanager(environ)
        
        # our add and delete hooks
        environ["psid.rtree.add"] = dm.add
        environ["psid.rtree.add"] = dm.delete
        
        # for debugging remove
        def error_callback(exc_info):
            pass
        def ok_callback():
            pass
        return catch_errors(self.app, environ, start_response,
                            error_callback, ok_callback)


class RtreeProxy(DictMixin):
    """
    A wrapper around an rtree, and index implementation
    """
    def __init__(self, dm, rtree, id_index):
        self.rtree = rtree
        self.dm = dm
        self.id_index = id_index

    def __getitem__(self, item):
        return self.id_index.get(item)

    def __setitem__(self, item, bounds):
        self.id_index[item] = bounds
        self.dm.add(item, bounds)

    def __delitem__(self, item):
        bounds = self.id_index.get(item)
        self.dm.delete(item, tuple(bounds))
        del self.id_index[item]

    def keys(self):
        return self.id_index.keys()

    def intersection(self, bounds):
        return self.rtree.intersection(bounds)

    def nearest(self, bounds, howmany):
        return self.rtree.nearest(bounds, howmany)



def zodb_rindex_handler(environ, store=STORE_ID, key=None):
    root = environ['zodb.root']
    store = root.get(store)
    rindex = store[key]
    return rindex


class RtreeIndexComponent(TMRtreeWrapper):
    """
    A wrapper that includes an rtree and an reverse index for looking
    up document ids

    rindex -- a callable that returns an object that may be used as a
              reverse index
    """
    def __init__(self, app, base_path, rindex=None, rindex_key="default", clear_index=False):
        super(RtreeIndexComponent, self).__init__(app, base_path, clear_index=False)
        self.rindex_handler = rindex
        self.rindex_key = rindex_key

    def __call__(self, environ, start_response):
        dm = self._init_datamanager(environ)
        rindex = self.rindex_handler(environ, key=self.rindex_key)
        environ["psid.rtree"] = RtreeProxy(dm, environ['psid.rtree_raw'], rindex)

        # do any cleanup here
        def error_callback(exc_info):
            self.dm = None
        def ok_callback():
            self.dm = None
        return catch_errors(self.app, environ, start_response,
                            error_callback, ok_callback)

def proc_basepath(path):
    if path.find(":") >= 0:
        dist, path = path.split(':')
        req = pkg_resources.Requirement.parse(dist)
        path = pkg_resources.resource_filename(req, path)
    return path

def make_rtree_middleware(app, global_conf, base_path=None, clear_index=False, mw_class=RtreeWrapper, **kw):
    conf = global_conf.copy()
    conf.update(kw)
    clear_index = global_conf.get('clear_index', clear_index)

    if base_path is None:
        base_path = conf.get('data_path')

    base_path = proc_basepath(base_path)
    return mw_class(app, base_path, clear_index=clear_index)

make_tmrtree_middleware=partial(make_rtree_middleware, mw_class=TMRtreeWrapper)

RINDEX="reverse_index"

def load_ep(spec, group):
    scheme, spec = spec.split(":", 1)
    #@@ resolver option?
    assert scheme == 'egg', ValueError('zodb init must be an entry point')
    dist, ep = spec.split('#')
    return pkg_resources.load_entry_point(dist, group, ep)

def zodb_init(root, conf, store_id=STORE_ID, btree='BTrees.IOBTree:IOBTree'):
    """
    initializes the zodb for a single rtree reverse index

    this function should only ever be run once by zodbmiddleware
    """
    store = root.setdefault(store_id, PersistentMapping())
    btree_spec = conf.get('psid_btree', btree)
    btree = resolver.resolve(btree_spec)
    key = conf['psid_rindex_key']
    assert store.get(key) is None, "Your psid_rindex_key is not unique"
    store[key] = btree()

def make_rtree_index_component(app, global_conf, clear_index=False, **kwargs):
    conf = global_conf.copy()
    clear_index = conf.get('clear_index', clear_index)
    rindex_handler = conf.get("rindex_handler", "egg:psid#zodb")
    
    # @@ default to zodb
    assert rindex_handler is not None, ValueError("you must specify an rindex handler")
    handler = load_ep(rindex_handler, "psid.%s" %RINDEX)
    base_path = kwargs.get('base_path')
    if base_path is None:
        base_path = conf.get('data_path')


    base_path = proc_basepath(base_path)
    rindex_key = conf['psid_rindex_key']
    return RtreeIndexComponent(app, base_path, rindex=handler, rindex_key=rindex_key, clear_index=clear_index)
