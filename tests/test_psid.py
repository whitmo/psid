from webtest import TestApp
from psid.app import make_app

app = TestApp(make_app({}))

def test_basic():
    app.get('/', status=200)
