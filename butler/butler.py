import functools
from os import path
from twisted.internet import defer
from txjsonrpc import jsonrpclib
from txjsonrpc.web.jsonrpc import JSONRPC

import txspotify

def method(f):
    @functools.wraps(f)
    def g(*args, **kwds):
        try:
            return f(*args, **kwds)
        except TypeError as e:
            raise jsonrpclib.Fault(jsonrpclib.INVALID_METHOD_PARAMS, str(e))
    g._public = True
    return g

class Butler(JSONRPC):
    def __init__(self):
        self._name = 'butler'
        self._spotify = txspotify.Session(self._name)

    @method
    @defer.inlineCallbacks
    def spotify_login(self, username, password):
        """Log in to Spotify with the username and password."""
        try:
            yield self._spotify.login(username, password)
        except txspotify.SpotifyError as e:
            raise jsonrpclib.Fault(e.error_type, str(e))

    def _getFunction(self, functionPath):
        """Find a method and call that one."""
        f = getattr(self, functionPath, None)
        if f is None or getattr(f, '_public', None) is None:
            raise jsonrpclib.NoSuchFunction(jsonrpclib.METHOD_NOT_FOUND,
                "function %s not found" % functionPath)
        return f
