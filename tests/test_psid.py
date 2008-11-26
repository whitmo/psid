from webtest import TestApp
from paste.deploy.loadwsgi import loadapp
import simplejson
import os
import pkg_resources

dist = pkg_resources.Requirement.parse('psid')

app = None

def setup(tc):
    global app
    doc_path = pkg_resources.resource_filename(dist, 'docs')
    gc = dict(data_path='psid:tests')
    app2 = loadapp('config:psid-conf.ini',
                   name='test',
                   **dict(global_conf=gc, relative_to=doc_path))
    
    app = TestApp(app2)
    teardown()

def teardown():
    path = pkg_resources.resource_filename(dist, 'tests')
    try:
        os.unlink(os.path.join(path, 'rtree.dat'))
        os.unlink(os.path.join(path, 'rtree.idx'))
    except OSError:
        pass
    
def test_empty_index_query():
    res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
    assert res.json == [], "Not an empty list"
    
def test_basic():
    app.get('/', status=200)
    
def test_adding_by_post():
    item = simplejson.dumps(dict(id=1, bbox=[0,0,10,10]))
    res = app.post('/', item)
    assert res.body == '/1'

def test_query():
    res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
    assert res.json == [1]

def test_basic_item_view():
    res = app.get('/1', status=200)
    res = app.get('/2', status=404)

def test_delete():
    res = app.delete('/1', status=200)

def test_empty_delete():
    res = app.delete('/2', status=404)

def test_add_query_roundtrip():
    record1 = dict(id=1, bbox=[0,0,9,9])
    record2 = dict(id=2, bbox=[0,0,9,9])
    json_item = simplejson.dumps(record1)
    res = app.post('/', json_item)
    assert res.body == '/1', ValueError(res.body)

    res = app.get('/1', status=200)
    assert res.json == record1, ValueError(res.json)

    res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
    assert res.json == [1], ValueError(res.json)

    json_item = simplejson.dumps(record2)
    res = app.post('/', json_item)
    assert res.body == '/2', ValueError(res.body)

    res = app.get('/2', status=200)
    assert res.json == record2, ValueError(res.json)

    res = app.get('/?maxx=10&maxy=10&minx=0&miny=0&new=1', status=200)
    assert len(res.json) == 2 and 2 in res.json, ValueError(res.json)

    app.delete('/2', status=200)
    app.delete('/1', status=200)

def test_newpost_queryable():
    record1 = dict(id=1, bbox=[0,0,9,9])    
    json_item = simplejson.dumps(record1)
    res = app.post('/', json_item)
    res = app.get('/?maxx=10&maxy=10&minx=0&miny=0', status=200)
    assert res.json == [1], ValueError(res.json)

def test_service_doc():
    res = app.get('/service-doc', status=200)

def test_nearest():
    records = [dict(id=1, bbox=[0,0,9,9]), dict(id=2, bbox=[0,0,9,9])]
    for record in records:
        json_item = simplejson.dumps(record)
        res = app.post('/', json_item)
    res = app.get('/nearest?maxx=10&maxy=10&minx=0&miny=0&n=1', status=200)
