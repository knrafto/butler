"""JSON endpoints."""
import functools
import inspect
import json

from werkzeug.routing import Map, Rule, Submount
from werkzeug.utils import ArgumentValidationError, validate_arguments
from werkzeug.wsgi import responder
from werkzeug.wrappers import Request, Response

class Encoder(json.JSONEncoder):
    """The default JSON encoder. When encoding objects, if the object
    has a :attribute:json property, it will be used instead of the
    object.

    >>> class Spam(object):
    ...     def json(self):
    ...         return 'eggs'
    ...
    >>> Encoder().encode({'spam': Spam()})
    '{"spam": "eggs"}'
    """
    def default(self, obj):
        try:
            encode = obj.json
        except AttributeError:
            return super(Encoder, self).default(obj)
        else:
            return encode()

class JSONRequest(Request):
    """A JSON request.

    >>> from werkzeug.test import EnvironBuilder
    >>> environ = EnvironBuilder(
    ...     content_type='application/json',
    ...     data='{"spam": 1, "eggs": 2}').get_environ()
    >>> d = JSONRequest(environ).json()
    >>> d['spam']
    1
    >>> d['eggs']
    2
    """
    max_content_length = 1024 * 1024 # 1MB

    def json(self):
        if self.headers.get('content-type') == 'application/json':
            return json.loads(self.get_data(as_text=True))

class JSONResponse(Response):
    """A JSON response.

    >>> class Spam(object):
    ...     def json(self):
    ...         return 'eggs'
    ...
    >>> response = JSONResponse({"spam": Spam()}, status=200)
    >>> response.content_type
    'application/json'
    >>> response.get_data()
    b'{"spam": "eggs"}'
    """
    def __init__(self, result, encoder=None, **kwds):
        super(JSONResponse, self).__init__(**kwds)
        if encoder is None:
            encoder = Encoder()
        self.response = encoder.iterencode(result)
        self.content_type = 'application/json'

class Endpoint:
    """An JSON endpoint that can be used as a normal function.

    :param string: The :class:Rule string.
    :param f: The wrapped function.
    :param response_handler: A function that, if present, will be
        called with the result of the wrapped function.
    :param error_handler: A function that, if present, will be
        called with any exception the wrapped function raises.
    :param kwds: Keyword arguments for :class:Rule.

    >>> from werkzeug.test import Client
    >>> def foo(x=0, y=0):
    ...     return {'result': x + y}
    ...
    >>> f = Endpoint('/<int:x>/', foo, encoder=Encoder(sort_keys=True))
    >>> str(f.rule)
    '/<int:x>/'
    >>> f(3, 2)
    {'result': 5}
    >>> c = Client(f.dispatch({"x": 3}), Response)
    >>> c.get('/', data='{"y": 2}',
    ...       content_type='application/json').data
    b'{"result": 5}'
    >>> c.get('/', data='{"y": "spam"}',
    ...       content_type='application/json').data # doctest: +ELLIPSIS
    b'{"message": "...", "status": 500}'
    """
    def __init__(self, string, f, encoder=None, **kwds):
        self.rule = Rule(string, endpoint=self, **kwds)
        self.f = f
        self.encoder = encoder
        functools.update_wrapper(self, f)

    def __call__(self, *args, **kwds):
        """Call the wrapped function normally."""
        return self.f(*args, **kwds)

    def dispatch(self, kwds):
        """Dispatch a request and pass URL arguments to the wrapped
        function. Any JSON object in the request body is passed as
        well if parsed correctly. Returns a WSGI application.
        """
        @responder
        def app(environ, start_reponse):
            status = None
            try:
                result = self._marshal(JSONRequest(environ), kwds)
            except Exception as e:
                try:
                    status = e.status
                except AttributeError:
                    status = 500 # Internal server error
                result = {
                    'status': status,
                    'message': str(e)
                }
            return JSONResponse(result, encoder=self.encoder, status=status)
        return app

    def _marshal(self, request, kwds):
        try:
            body = request.json()
            if isinstance(body, dict):
                kwds.update(body)
        except ValueError:
            pass
        try:
            args, kwds = validate_arguments(self.f, (), kwds)
        except ArgumentValidationError as e:
            raise BadRequest(e)
        return self.f(*args, **kwds)

def endpoint(string, **kwds):
    return functools.partial(Endpoint, string, **kwds)

class Dispatcher(object):
    """A WSGI application that dispatches requests to delegates.

    Each delegate is identified by a name. The delegate URLs are
    mounted in a submount identified by the delegate name.

    Delegate endpoints will be called with any dependencies they
    require, a Request object, and any keyword arguments from the
    URL. They should return a Response object.

    :param delegates: A dictionary of delegates.

    >>> from werkzeug.test import Client
    >>> from werkzeug.wrappers import Response
    >>> class Spam(object):
    ...     @endpoint('/<int:x>/', encoder=Encoder(sort_keys=True))
    ...     def foo(x=0):
    ...         return {'result': x + 2}
    ...
    >>> class Eggs(object):
    ...     @endpoint('/<string:s>/', encoder=Encoder(sort_keys=True))
    ...     def foo(s=''):
    ...         raise BadRequest(s)
    ...
    >>> dispatcher = Dispatcher({
    ...     'spam': Spam(),
    ...     'eggs': Eggs()
    ... })
    >>> c = Client(dispatcher, Response)
    >>> c.get('/spam/3/').data
    b'{"result": 5}'
    >>> c.get('/eggs/ni/').data
    b'{"message": "ni", "status": 400}'
    """
    def __init__(self, delegates):
        self.delegates = delegates
        self.url_map = Map([
            Submount('/' + name, [
                f.rule for _, f in inspect.getmembers(
                    delegate, lambda f: isinstance(f, Endpoint)
                )
            ])
            for name, delegate in self.delegates.items()
        ])

    @responder
    def __call__(self, environ, start_reponse):
        """Respond to a request."""
        urls = self.url_map.bind_to_environ(environ)
        return urls.dispatch(lambda f, kwds: f.dispatch(kwds))

class HTTPException(Exception):
    status = 400

class BadRequest(HTTPException):
    status = 400
