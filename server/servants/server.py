import functools

import gevent
import socketio
import socketio.namespace
import socketio.server

import butler

class Server(butler.Servant):
    """A web server that communicates through Socket.IO."""
    name = 'server'

    def __init__(self, butler, config):
        super(Server, self).__init__(butler, config)
        address = config.get('address', '127.0.0.1:26532')
        server = socketio.server.SocketIOServer(
            address, self._respond, policy_server=False)
        gevent.spawn(server.serve_forever())

    def _respond(self, environ, start_response):
        if environ['PATH_INFO'].startswith('/socket.io'):
            socketio.socketio_manage(environ, {'': Namespace}, self.butler)
        else:
            start_response('404 Not Found', [])
        return ()

class Namespace(socketio.namespace.BaseNamespace):
    def initialize(self):
        self.butler = self.request
        self.listeners = []

    def disconnect(self):
        for event, listener in self.listeners:
            self.butler.off(event, listener)

    def process_event(self, packet):
        try:
            name = packet['name']
            data = packet['args'][0]
            if name == 'event':
                self.butler.emit(data['name'], *data['args'], **data['kwds'])
            elif name == 'request':
                result = self.butler.call(
                    data['method'], *data['args'], **data['kwds'])
                self.emit('response', {
                    'id': data['id'],
                    'result': result
                })
            elif name == 'subscribe':
                event = data['name']
                listener = functools.partial(self.notify, event)
                self.listeners.append((event, listener))
                self.butler.on(event, listener)
            else:
                raise ValueError("unknown packet name '%s'" % name)
        except Exception as e:
            self.error(e.__class__.__name__, str(e))

    def notify(self, event, *args, **kwds):
        self.emit('event', {
            'name': event,
            'args': args,
            'kwds': kwds
        })
