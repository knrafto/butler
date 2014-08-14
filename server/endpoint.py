import functools
import json
import inspect

from werkzeug.exceptions import InternalServerError
from werkzeug.routing import Map, Rule, Submount
from werkzeug.wsgi import responder
from werkzeug.wrappers import Response

def route(url):
    """A decorator that exposes a function as an endpoint with the
    specified URL, in Werkzeug format.
    """
    def g(f):
        if not hasattr(f, '_urls'):
            f._urls = []
        f._urls.append(url)
        return f
    return g

def routes(obj):
    """Return the list of Werkzeug rules for an object.

    >>> class Plugin(object):
    ...     @route('/')
    ...     def root(): pass
    ...     @route('/<int:year>/<int:month>/')
    ...     @route('/<int:year>/<int:month>/<int:day>/')
    ...     def archive(year=None, month=None, day=None): pass
    ...     def hidden(): pass
    ...
    >>> [str(r) for r in routes(Plugin())]
    ['/<int:year>/<int:month>/<int:day>/', '/<int:year>/<int:month>/', '/']
    """
    return [
        Rule(url, endpoint=f)
        for name, f in inspect.getmembers(
            obj, lambda f: callable(f) and hasattr(f, '_urls')
        )
        for url in f._urls
    ]

def require(*names):
    """A decorator that declares the names of the resources that this
    endpoint needs. The required dependencies will be passed to the
    function in order. If the string '*' is passed, a dictionary of
    all resources will be injected.
    """
    def g(f):
        f._deps = names
        return f
    return g

class DependencyError(Exception):
    """Raised when a dependency cannot be found."""
    pass

def inject(f, resources):
    """Resolve all dependencies that a function needs using the
    given resources.

    >>> @require('spam', 'eggs')
    ... def foo(spam, eggs, x):
    ...     return spam + eggs + x
    ...
    >>> def bar(x):
    ...     return x
    ...
    >>> @require('spam', '*')
    ... def baz(spam, delegates, x):
    ...     return spam + delegates['eggs'] + x
    ...
    >>> r1 = {
    ...     'spam': 1,
    ...     'eggs': 2
    ... }
    >>> inject(foo, r1)(3)
    6
    >>> inject(bar, r1)(3)
    3
    >>> inject(baz, r1)(3)
    6
    >>> r2 = {
    ...     'spam': 1
    ... }
    >>> inject(foo, r2)(3)
    Traceback (most recent call last):
       ...
    DependencyError: Missing dependency 'eggs'
    """
    def resolve(dep):
        if dep == '*':
            return resources
        try:
            return resources[dep]
        except KeyError:
            raise DependencyError("Missing dependency '%s'" % dep)
    args = (resolve(dep) for dep in getattr(f, '_deps', ()))
    return functools.partial(f, *args)

class Dispatcher(object):
    """A WSGI application that dispatches requests to delegates.

    Each delegate is identified by a name, which will be used in
    dependency injection. The delegate URLs are mounting in a
    submount identified by the delegate name.

    All delegate endpoints should return a JSON-encodable Python
    object.

    >>> from werkzeug.test import Client
    >>> class Spam(object):
    ...    @route('/<int:id>/')
    ...    def echo(self, **kwds):
    ...        return kwds
    ...
    >>> class Knights(object):
    ...    @route('/<int:id>/')
    ...    @require('spam')
    ...    def echo(self, spam, id=0):
    ...        return spam.echo(id=id)
    ...
    >>> delegates = {
    ...     'spam': Spam(),
    ...     'knights': Knights()
    ... }
    >>> c = Client(Dispatcher(delegates))
    >>> app_iter, _, _ = c.get('/spam/2/')
    >>> ''.join(app_iter)
    '{"id": 2}'
    >>> app_iter, _, _ = c.get('/knights/4/')
    >>> ''.join(app_iter)
    '{"id": 4}'
    """
    def __init__(self, delegates):
        self.delegates = delegates
        self.url_map = Map([
            Submount('/' + name, routes(delegate))
                for name, delegate in self.delegates.iteritems()
        ])

    def dispatch(self, f, kwds):
        """Dispatch a request to the given function."""
        try:
            obj = inject(f, self.delegates)(**kwds)
            result = json.dumps(obj)
        except Exception as e:
            raise InternalServerError(str(e))
        return Response(result, content_type='application/json')

    @responder
    def __call__(self, environ, start_reponse):
        """Respond to a request."""
        urls = self.url_map.bind_to_environ(environ)
        return urls.dispatch(self.dispatch, catch_http_exceptions=True)
