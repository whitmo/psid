from webtest import TestApp
from psid.app import make_app
from paste.deploy.loadwsgi import loadapp
import simplejson
import os
import pkg_resources

dist = pkg_resources.Requirement.parse('psid')

app = None

def setup():
    global app
    doc_path = pkg_resources.resource_filename(dist, 'docs')
    gc = dict(data_path='psid:tests')
    app2 = loadapp('config:psid-conf.ini',
                   name='base',
                   **dict(global_conf=gc, relative_to=doc_path))
    
    app = TestApp(app2)
    try:
        teardown()
    except OSError, e:
        print e

def teardown():
    data = pkg_resources.resource_filename(dist, 'tests')
    os.unlink(os.path.join(data, 'rtree.dat'))
    os.unlink(os.path.join(data, 'rtree.idx'))

# def test_add_query_roundtrip():
#     item = simplejson.dumps(dict(id=1, bbox=[0,0,10,10]))
#     res = app.post('/', item)
#     assert res.body == '/1'
#     res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
#     assert res.json == [1]

def test_empty_index_query():
    res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
    assert res.json == [], "Not an empty list"
    
def test_basic():
    app.get('/', status=200)
    

def test_post():
    item = simplejson.dumps(dict(id=1, bbox=[0,0,10,10]))
    res = app.post('/', item)
    assert res.body == '/1'

def test_query():
    res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
    assert res.json == [1]

def test_basic_item_view():
    res = app.get('/1', status=200)

def test_delete():
    res = app.delete('/1')

# def test_add_query_roundtrip():
#     item = simplejson.dumps(dict(id=1, bbox=[0,0,10,10]))
#     res = app.post('/', item)
#     assert res.body == '/1'
#     res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
#     assert res.json == [1]

    




