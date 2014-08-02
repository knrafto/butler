import functools
import xmlrpclib

from twisted.internet import defer, reactor
from twisted.web import xmlrpc

def method(f):
    @functools.wraps(f)
    def g(*args, **kwds):
        try:
            return f(*args, **kwds)
        except TypeError as e:
            raise xmlrpc.Fault(xmlrpclib.INVALID_METHOD_PARAMS, str(e))
    g._public = True
    return g

def setTimeout(deferred, seconds):
    delayedCall = reactor.callLater(seconds, deferred.cancel)
    def gotResult(result):
        if delayedCall.active():
            delayedCall.cancel()
        return result
    def trapCancelledError(failure):
        r = failure.trap(defer.CancelledError)
        raise xmlrpc.Fault(50, "operation timed out")
    deferred.addBoth(gotResult)
    deferred.addErrback(trapCancelledError)

class Handler(xmlrpc.XMLRPC):
    def lookupProcedure(self, functionPath):
        """Lookup a method."""
        f = getattr(self, functionPath, None)
        if not getattr(f, '_public', False):
            raise xmlrpc.NoSuchFunction(xmlrpclib.METHOD_NOT_FOUND,
                "function %s not found" % functionPath)
        return f

    def listProcedures(self):
        """List all procedures."""
        if not hasattr(self, '_procedures'):
            self._procedures = []
            for key in dir(self):
                if hasattr(f, '_public'):
                    self._procedures.append(key)
        return self._procedures

