from os import path
from twisted.internet import defer
from txjsonrpc import jsonrpclib
from txjsonrpc.web.jsonrpc import JSONRPC

import txspotify

def method(f):
    g = defer.inlineCallbacks(f)
    g._public = True
    return g

class Butler(JSONRPC):
    def __init__(self):
        self._name = 'butler'
        self._spotify = txspotify.Session(self._name)

    @method
    def spotify_login(self, username=None, password=None):
        try:
            yield self._spotify.login(username, password)
        except txspotify.SpotifyError as e:
            raise jsonrpclib.Fault(e.error_type, str(e))

    def _getFunction(self, functionPath):
        f = getattr(self, functionPath, None)
        if f is None or getattr(f, '_public', None) is None:
            raise jsonrpclib.NoSuchFunction(jsonrpclib.METHOD_NOT_FOUND,
                "function %s not found" % functionPath)
        return f
