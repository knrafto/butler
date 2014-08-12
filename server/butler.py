#!/usr/bin/env python
from __future__ import print_function

def serve(config):
    import gevent
    import gevent.wsgi
    import gevent.queue
    from tinyrpc.dispatch import RPCDispatcher
    from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
    from tinyrpc.transports.wsgi import WsgiServerTransport
    from tinyrpc.server.gevent import RPCServerGreenlets

    from butler import libspotify

    server_config = config['server']

    handlers = {
        'spotify': libspotify.Spotify
    }

    dispatcher = RPCDispatcher()
    for prefix, cls in handlers.iteritems():
        handler_config = config.get(prefix, {})
        handler = cls(handler_config)
        dispatcher.register_instance(handler, prefix + '.')

    transport = WsgiServerTransport(queue_class=gevent.queue.Queue)

    wsgi_server = gevent.wsgi.WSGIServer(
        server_config['address'], transport.handle)
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

def ask(config, method, *args):
    from tinyrpc.exc import RPCError
    from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
    from tinyrpc.transports.http import HttpPostClientTransport
    from tinyrpc import RPCClient

    server_config = config['server']

    rpc_client = RPCClient(
        JSONRPCProtocol(),
        HttpPostClientTransport('http://' + server_config['address'])
    )

    try:
        result = rpc_client.call(method, args, {})
    except RPCError as e:
        print(e.message, file=sys.stderr)
        sys.exit(1)
    else:
        print(result)

if __name__ == '__main__':
    import json
    import os
    import sys

    # TODO: nicer errors
    config_file = open(
        os.path.expanduser(os.path.join('~', '.config', 'butler', 'butler.cfg')))
    config = json.load(config_file)
    config_file.close()

    if len(sys.argv) > 1:
        ask(config, sys.argv[1], *sys.argv[2:])
    else:
        serve(config)
