from __future__ import print_function

import functools
import inspect
import sys
import traceback

from werkzeug.exceptions import InternalServerError, HTTPException
from werkzeug.routing import Map, Rule, Submount
from werkzeug.wsgi import responder
from werkzeug.wrappers import Request

def route(string, **kwds):
    """A decorator that exposes a function as an endpoint with the
    specified URL, in Werkzeug Rule format.
    """
    def g(f):
        if not hasattr(f, '_routes'):
            f._routes = []
        f._routes.append((string, kwds))
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
        Rule(string, endpoint=f, **kwds)
        for name, f in inspect.getmembers(
            obj, lambda f: callable(f) and hasattr(f, '_routes')
        )
        for (string, kwds) in f._routes
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

    Delegate endpoints will be called with any dependencies they
    require, a Request object, and any keyword arguments from the
    URL. They should return a Response object.

    >>> from werkzeug.test import Client
    >>> from werkzeug.wrappers import Response
    >>> class Spam(object):
    ...    @route('/<int:id>/')
    ...    def spam(self, request, id=0):
    ...        return Response(str(id))
    ...
    >>> class Knights(object):
    ...    @route('/<int:id>/', methods=["POST"])
    ...    @require('spam')
    ...    def knights(self, spam, request, id=0):
    ...        return spam.spam(request, id=id)
    ...
    >>> delegates = {
    ...     'spam': Spam(),
    ...     'knights': Knights()
    ... }
    >>> c = Client(Dispatcher(delegates))
    >>> app_iter, _, _ = c.get('/spam/2/')
    >>> ''.join(app_iter)
    '2'
    >>> app_iter, _, _ = c.post('/knights/4/')
    >>> ''.join(app_iter)
    '4'
    """
    def __init__(self, delegates):
        self.delegates = delegates
        self.url_map = Map([
            Submount('/' + name, routes(delegate))
                for name, delegate in self.delegates.iteritems()
        ])

    @responder
    def __call__(self, environ, start_reponse):
        """Respond to a request."""
        request = Request(environ)
        urls = self.url_map.bind_to_environ(environ)

        def dispatch(f, kwds):
            try:
                return inject(f, self.delegates)(request, **kwds)
            except HTTPException:
                raise
            except Exception:
                traceback.print_exc()
                raise InternalServerError()

        return urls.dispatch(dispatch, catch_http_exceptions=True)
