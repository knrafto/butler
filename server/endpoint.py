import functools
import inspect
import sys

from werkzeug.exceptions import InternalServerError
from werkzeug.routing import Map, Rule, Submount
from werkzeug.utils import ArgumentValidationError, validate_arguments
from werkzeug.wsgi import responder
from werkzeug.wrappers import Request, Response

def curry(f):
    def curried(*args, **kwds):
        return functools.partial(f, *args, **kwds)
    return curried

class Endpoint(object):
    """An HTTP endpoint that can be used as a normal function.

    :param string: The :class:Rule string.
    :param f: The wrapped function.
    :param response_handler: A function that, if present, will be
        called with the result of the wrapped function.
    :param error_handler: A function that, if present, will be
        called with any exception the wrapped function raises.
    :param kwds: Keyword arguments for :class:Rule.

    >>> def foo(x=0):
    ...     return x + 2
    ...
    >>> f = Endpoint('/<int:x>/', foo,
    ...              response_handler=str,
    ...              error_handler=type)
    >>> str(f.rule)
    '/<int:x>/'
    >>> f(3)
    5
    >>> f.dispatch(3)
    '5'
    >>> f.dispatch('spam')
    <type 'exceptions.TypeError'>
    """

    rule = None
    """The :class:Rule for routing."""

    def __init__(self, string, f,
                 response_handler=None, error_handler=None,
                 **kwds):
        self.rule = Rule(string, endpoint=self, **kwds)
        self.f = f
        self.response_handler = response_handler
        self.error_handler = error_handler
        functools.update_wrapper(self, f)

    def __call__(self, *args, **kwds):
        """Call the wrapped function normally."""
        return self.f(*args, **kwds)

    def dispatch(self, *args, **kwds):
        """Dispatch a request and pass URL arguments to the wrapped
        function. Any form or query values will be passed as well.

        If the function returns a value, :attribute:response_handler
        will be called with the result. If the function raises an
        exception, :attribute:error_handler will be called with the
        exception object. These methods should return a WSGI
        application, such as a :class:Response object.
        """
        try:
            args, kwds = validate_arguments(self.f, args, kwds)
        except ArgumentValidationError:
            pass # TODO

        try:
            try:
                result = self.f(*args, **kwds)
            except:
                if self.error_handler:
                    result = self.error_handler(sys.exc_info()[1])
            else:
                if self.response_handler:
                    result = self.response_handler(result)
            return result
        except Exception as e:
            return InternalServerError(str(e))

endpoint = curry(Endpoint)


class Dispatcher(object):
    """A WSGI application that dispatches requests to delegates.

    Each delegate is identified by a name. The delegate URLs are
    mounted in a submount identified by the delegate name.

    Delegate endpoints will be called with any dependencies they
    require, a Request object, and any keyword arguments from the
    URL. They should return a Response object.

    :param delegates: A dictionary of delegates.

    >>> from werkzeug.exceptions import InternalServerError
    >>> from werkzeug.test import Client
    >>> from werkzeug.wrappers import Response
    >>> class Spam(object):
    ...     @endpoint('/<int:x>/', response_handler=Response)
    ...     def foo(x=0):
    ...         return str(x + 2)
    ...
    >>> class Eggs(object):
    ...     @endpoint('/<string:s>/',
    ...               error_handler=InternalServerError)
    ...     def foo(s=''):
    ...         raise Exception('ni')
    ...
    >>> dispatcher = Dispatcher({
    ...     'spam': Spam(),
    ...     'eggs': Eggs()
    ... })
    >>> c = Client(dispatcher, Response)
    >>> c.get('/spam/3/').data
    '5'
    >>> c.get('/eggs/ni/').data[:14]
    '<!DOCTYPE HTML'
    """
    def __init__(self, delegates):
        self.delegates = delegates
        self.url_map = Map([
            Submount('/' + name, [
                f.rule for _, f in inspect.getmembers(
                    delegate, lambda f: isinstance(f, Endpoint)
                )
            ])
            for name, delegate in self.delegates.iteritems()
        ])

    @responder
    def __call__(self, environ, start_reponse):
        """Respond to a request."""
        request = Request(environ)
        urls = self.url_map.bind_to_environ(environ)

        def dispatch(f, kwds):
            kwds.update(request.values.to_dict())
            return f.dispatch(**kwds)

        return urls.dispatch(dispatch)
