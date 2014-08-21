import unittest

import simplejson as json
from werkzeug.exceptions import Unauthorized
from werkzeug.test import Client, EnvironBuilder
from werkzeug.wrappers import Response

from butler import routing
from butler.options import Options
from butler.routing import endpoint

class RoutingTestCase(unittest.TestCase):
    def test_request(self):
        data = {
            'foo': 42,
            'bar': 'blub'
        }
        builder = EnvironBuilder(
            data=json.dumps(data),
            content_type='application/json')
        request = routing.JSONRequest(builder.get_environ())
        self.assertEqual(request.json(), data)

        builder = EnvironBuilder(data=json.dumps(data))
        request = routing.JSONRequest(builder.get_environ())
        self.assertEqual(request.json(), None)

    def test_response(self):
        class Spam:
            def json(self):
                return Eggs()

        class Eggs:
            def json(self):
                return 'eggs'

        data = {
            'foo': 42,
            'bar': Spam()
        }
        response = routing.JSONResponse(data)
        self.assertEqual(json.loads(response.get_data(as_text=True)), {
            'foo': 42,
            'bar': 'eggs'
        })
        self.assertEqual(response.content_type, 'application/json')

        response = routing.JSONResponse()
        self.assertEqual(response.get_data(), '')

    def test_dispatcher(self):
        class Spam(object):
            def __init__(self, baz):
                self.baz = baz

            @endpoint('/<int:x>/', methods=['GET', 'POST'])
            def foo(self, **kwds):
                options = Options(kwds)
                return {
                    'foo': options.int('x'),
                    'bar': options.str('bar'),
                    'baz': self.baz
                }

        class Eggs(object):
            @endpoint('/')
            def bar(self, **kwds):
                raise Unauthorized('unauthorized')

        dispatcher = routing.Dispatcher({
            'spam': Spam('ni'),
            'eggs': Eggs()
        })

        c = Client(dispatcher, Response)
        response = c.post(
            '/spam/42/',
            data='{"bar": "blub"}',
            content_type='application/json')
        response_data = json.loads(response.get_data())
        self.assertEqual(response_data, {
            'foo': 42,
            'bar': 'blub',
            'baz': 'ni'
        })

        response = c.get('/spam/42/', query_string='bar=blub')
        response_data = json.loads(response.get_data())
        self.assertEqual(response_data, {
            'foo': 42,
            'bar': 'blub',
            'baz': 'ni'
        })
        response = c.get('/eggs/')
        response_data = json.loads(response.get_data())
        self.assertEqual(response_data, {
            'status': 401,
            'message': 'unauthorized'
        })

        response = c.get('/eggs/ni/')
        self.assertEqual(response.status_code, 404)

        response = c.post(
            '/spam/42/',
            data='{"bar": "blub"',
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
