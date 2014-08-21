"""JSON endpoints"""
import inspect

import simplejson as json
from werkzeug.exceptions import BadRequest, HTTPException
from werkzeug.routing import Map, Rule, Submount
from werkzeug.wsgi import responder
from werkzeug.wrappers import Request, Response

class DefaultEncoder(json.JSONEncoder):
    """The default JSON encoder. When encoding objects, if the object
    has a :attribute:json property, it will be used instead of the
    object.
    """
    def default(self, obj):
        try:
            encode = obj.json
        except AttributeError:
            return super(DefaultEncoder, self).default(obj)
        else:
            return encode()

defaultEncoder = DefaultEncoder()

class JSONRequest(Request):
    max_content_length = 1024 * 1024 # 1MB

    def json(self):
        if self.headers.get('content-type') == 'application/json':
            return json.loads(self.get_data(as_text=True))

class JSONResponse(Response):
    def __init__(self, result=None, **kwds):
        super(JSONResponse, self).__init__(**kwds)
        if result is not None:
            self.response = defaultEncoder.iterencode(result)
            self.content_type = 'application/json'

def endpoint(string, **options):
    def decorator(f):
        f._route = Rule(string, **options)
        return f
    return decorator

class Dispatcher(object):
    """A WSGI application that dispatches requests to delegates.

    Each delegate is identified by a name. The delegate URLs are
    mounted in a submount identified by the delegate name.
    """
    def __init__(self, delegates):
        self.delegates = delegates
        self.url_map = Map([
            Submount('/' + name, list(self._rules(delegate)))
            for name, delegate in self.delegates.items()])

    def _rules(self, obj):
        for _, f in inspect.getmembers(
                obj, lambda f: callable(f) and hasattr(f, '_route')):
            rule = f._route
            rule.endpoint = f
            yield rule

    def _dispatch(self, f, request, kwds):
        status = None
        try:
            args = None
            if request.method == 'GET':
                args = request.args.to_dict()
            elif request.method == 'POST':
                try:
                    args = request.json()
                except (TypeError, ValueError):
                    raise BadRequest
            if args:
                kwds.update(args)
            result = f(**kwds)
        except HTTPException as e:
            status = e.code
            result = {
                'status': status,
                'message': e.description
            }
        return JSONResponse(result, status=status)

    @responder
    def __call__(self, environ, start_reponse):
        urls = self.url_map.bind_to_environ(environ)
        request = JSONRequest(environ)
        return urls.dispatch(lambda f, kwds: self._dispatch(f, request, kwds),
                             catch_http_exceptions=True)
