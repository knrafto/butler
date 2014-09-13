import mock
import unittest

import socketio.virtsocket

import butler
from servants import server

class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.butler = mock.Mock(spec=butler.Butler)
        self.socket = mock.Mock()
        environ = {'socketio': self.socket}
        self.ns = server.Namespace(environ, '', request=self.butler)
        self.ns.initialize()

    def test_event(self):
        self.ns.process_event({
            'type': 'event',
            'name': 'event',
            'args': [{
                'name': 'foo.bar',
                'args': ['spam', 'eggs'],
                'kwds': {'knights': 'ni'}
            }]
        })
        self.assertFalse(self.socket.error.called)
        self.butler.emit.assert_called_with(
            'foo.bar', 'spam', 'eggs', knights='ni')

    def test_request(self):
        self.butler.call.return_value = 42
        self.ns.process_event({
            'type': 'event',
            'name': 'request',
            'args': [{
                'method': 'foo.bar',
                'id': 5,
                'args': ['spam', 'eggs'],
                'kwds': {'knights': 'ni'}
            }]
        })
        self.assertFalse(self.socket.error.called)
        self.butler.call.assert_called_with(
            'foo.bar', 'spam', 'eggs', knights='ni')
        self.socket.send_packet.assert_called_with({
            'type': 'event',
            'name': 'response',
            'endpoint': '',
            'args': ({
                'id': 5,
                'result': 42
            },)
        })

        self.butler.call.side_effect = Exception('bam')
        self.ns.process_event({
            'type': 'event',
            'name': 'request',
            'args': [{
                'method': 'foo.bar',
                'id': 5,
                'args': ['spam', 'eggs'],
                'kwds': {'knights': 'ni'}
            }]
        })
        self.assertFalse(self.socket.error.called)
        self.butler.call.assert_called_with(
            'foo.bar', 'spam', 'eggs', knights='ni')
        self.socket.send_packet.assert_called_with({
            'type': 'event',
            'name': 'response',
            'endpoint': '',
            'args': ({
                'id': 5,
                'error': 'Exception: bam'
            },)
        })

    def test_subscribe(self):
        callbacks = []
        self.butler.on.side_effect = lambda event, f: callbacks.append(f)
        self.ns.process_event({
            'type': 'event',
            'name': 'subscribe',
            'args': [{
                'name': 'foo.bar'
            }]
        })
        self.assertFalse(self.socket.error.called)
        self.assertEqual(len(callbacks), 1)
        callbacks[0]('spam', 'eggs', knights='ni')

    def test_error(self):
        self.ns.process_event({
            'type': 'event',
            'name': 'nothing',
            'args': [{
                'method': 'foo.bar',
                'id': 5,
                'args': ['spam', 'eggs'],
                'kwds': {'knights': 'ni'}
            }]
        })
        self.socket.error.assert_called_with(
            'ValueError', "unknown packet name 'nothing'",
            msg_id=None, endpoint='', quiet=False)
