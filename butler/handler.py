import functools
import logging
import xmlrpclib

from twisted.internet import defer, reactor
from twisted.web import xmlrpc

def method(f):
    f._public = True
    return f

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

class Handler(object, xmlrpc.XMLRPC):
    def __init__(self, name, errback=None):
        self._name = name
        self._errback = errback
        self._logger = logging.getLogger(name)

    def lookupProcedure(self, functionPath):
        """Lookup a method."""
        f = getattr(self, functionPath, None)
        if not getattr(f, '_public', False):
            raise xmlrpc.NoSuchFunction(xmlrpclib.METHOD_NOT_FOUND,
                "function %s not found" % functionPath)

        def trapInvalidMethodParams(failure):
            failure.trap(TypeError)
            raise xmlrpc.Fault(xmlrpclib.INVALID_METHOD_PARAMS,
                               str(failure.value))

        def g(*args):
            self._logger.info('%s.%s(%s)',
                               self._name, functionPath, ', '.join(args))
            d = defer.maybeDeferred(f, *args)
            d.addErrback(trapInvalidMethodParams)
            if self._errback:
                d.addErrback(self._errback)
            d.addBoth(self._log, functionPath, *args)
            d.addCallback(self._encode)
            return d

        return g

    def listProcedures(self):
        """List all procedures."""
        if not hasattr(self, '_procedures'):
            self._procedures = []
            for key in dir(self):
                if hasattr(f, '_public'):
                    self._procedures.append(key)
        return self._procedures

    def _log(self, result, functionPath, *args):
        """Log the result of an RPC call."""
        self._logger.info('[%s.%s(%s)]: %s',
                           self._name, functionPath, ', '.join(args),
                           repr(result))
        return result

    def _encode(self, result):
        """Encode the result of an RPC call."""
        if result is None:
            return True
        try:
            return result.encode_response()
        except (AttributeError, NotImplementedError):
            return result
