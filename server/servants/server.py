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

    def disconnect(self, silent):
        for event, listener in self.listeners:
            self.butler.off(event, listener)

    def process_event(self, packet):
        try:
            name = packet['name']
            data = packet['args'][0]
            if name == 'event':
                self._event(**data)
            elif name == 'request':
                self._request(**data)
            elif name == 'subscribe':
                self._subscribe(**data)
            else:
                raise ValueError("unknown packet name '%s'" % name)
        except Exception as e:
            self.error(e.__class__.__name__, str(e))

    def _event(self, name, args=(), kwds=None):
        if kwds is None:
            kwds = {}
        self.butler.emit(name, *args, **kwds)

    def _request(self, id, method, args=(), kwds=None):
        if kwds is None:
            kwds = {}
        try:
            result = self.butler.call(method, *args, **kwds)
        except Exception as e:
            self.emit('response', {
                'id': id,
                'error': "%s: %s" % (e.__class__.__name__, str(e))
            })
        else:
            self.emit('response', {
                'id': id,
                'result': result
            })

    def _subscribe(self, name):
        listener = functools.partial(self.notify, name)
        self.listeners.append((name, listener))
        self.butler.on(name, listener)

    def notify(self, event, *args, **kwds):
        self.emit('event', {
            'name': event,
            'args': args,
            'kwds': kwds
        })
