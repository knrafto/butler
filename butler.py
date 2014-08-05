#!/usr/bin/env python

import os
import sys

def serve():
    import json
    import logging

    from twisted.internet import reactor
    from twisted.python import log
    from twisted.web import server, xmlrpc

    from butler import libspotify

    data_dir = os.path.expanduser(os.path.join('~', '.butler'))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    config_file = open(os.path.join(data_dir, 'butler.cfg'))
    config = json.load(config_file)
    config_file.close()

    logging.basicConfig(filename=os.path.join(data_dir, 'butler.log'))
    observer = log.PythonLoggingObserver(loggerName='twisted')
    observer.start()

    rpc = xmlrpc.XMLRPC()
    rpc.subHandlers = {
        'spotify': libspotify.Spotify(config)
    }

    # TODO: port and address
    reactor.listenTCP(6969, server.Site(rpc))
    reactor.run()
    return 0

def ask(method, *params):
    from twisted.internet import defer, reactor
    from twisted.web.xmlrpc import Proxy

    def printValue(value):
        print 'Result: %s' % str(value)
        if reactor.running:
            reactor.stop()

    def printError(error):
        print 'Error: %s' % str(error.value)
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
