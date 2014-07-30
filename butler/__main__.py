import sys

def serve():
    from twisted.internet import reactor
    from twisted.web import server

    from butler import Butler

    b = Butler()
    # TODO: port and address
    reactor.listenTCP(6969, server.Site(b))
    reactor.run()
    return 0

def ask(method, *params):
    from twisted.internet import defer, reactor
    from txjsonrpc import jsonrpclib
    from txjsonrpc.web.jsonrpc import Proxy

    def printValue(value):
        if value is None:
            print 'Success'
        else:
            print 'Result: %s' % str(value)
        if reactor.running:
            reactor.stop()

    def printError(error):
        e = error.value
        if isinstance(e, jsonrpclib.Fault):
            print 'Fault %i: %s' % (e.faultCode, str(e.faultString))
        else:
            print 'Error: %s' % str(e)
        if reactor.running:
            reactor.stop()

    proxy = Proxy('http://127.0.0.1:6969/')
    d = proxy.callRemote(method, *params)
    d.addCallbacks(printValue, printError)
    reactor.run()
    return 0

def main(argv):
    if len(argv) > 1:
        return ask(argv[1], *argv[2:])
    else:
        return serve()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
