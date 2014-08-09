#!/usr/bin/env python
from __future__ import print_function

def serve():
    import os
    import json

    import gevent
    import gevent.wsgi
    import gevent.queue
    from tinyrpc.dispatch import RPCDispatcher
    from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
    from tinyrpc.transports.wsgi import WsgiServerTransport
    from tinyrpc.server.gevent import RPCServerGreenlets

    from butler import libspotify

    config_file = open(
        os.path.expanduser(os.path.join('~', '.butler', 'butler.cfg')))
    config = json.load(config_file)
    config_file.close()

    handlers = {
        'spotify': libspotify.Spotify
    }

    dispatcher = RPCDispatcher()
    for prefix, cls in handlers.iteritems():
        handler_config = config.get(prefix, {})
        handler = cls(handler_config)
        dispatcher.register_instance(handler, prefix + '.')

    transport = WsgiServerTransport(queue_class=gevent.queue.Queue)

    # start wsgi server as a background greenlet
    wsgi_server = gevent.wsgi.WSGIServer(('127.0.0.1', 6969), transport.handle)
    gevent.spawn(wsgi_server.serve_forever)

    rpc_server = RPCServerGreenlets(
        transport,
        JSONRPCProtocol(),
        dispatcher
    )

    try:
        rpc_server.serve_forever()
    except KeyboardInterrupt:
        pass

def ask(method, *args):
    from tinyrpc.exc import RPCError
    from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
    from tinyrpc.transports.http import HttpPostClientTransport
    from tinyrpc import RPCClient

    rpc_client = RPCClient(
        JSONRPCProtocol(),
        HttpPostClientTransport('http://127.0.0.1:6969/')
    )

    try:
        result = rpc_client.call(method, args, {})
    except RPCError as e:
        print(e.message, file=sys.stderr)
        sys.exit(1)
    else:
        print(result)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        ask(sys.argv[1], *sys.argv[2:])
    else:
        serve()
