import unittest
import mock

import spotify
from werkzeug.exceptions import BadGateway, Unauthorized

from butler.options import Options
from butler.services.libspotify import Spotify

root = 'butler.services.libspotify.'

@mock.patch(root + 'spotify.Session', autospec=True)
@mock.patch(root + 'spotify.AlsaSink', autospec=True)
class SpotifyTestCase(unittest.TestCase):
    @mock.patch(root + 'spotify.Config')
    @mock.patch(root + 'os')
    def test_config(self, os_mock, config_mock, sink_mock, session_mock):
        os_mock.configure_mock(**{
            'path.expanduser.side_effect': lambda path: path,
            'path.exists.return_value': False
        })

        Spotify(Options({
            'spotify': {
                'cachedir': 'foo',
                'datadir': 'bar',
                'keyfile': 'baz'
            }
        }))

        config_instance = config_mock.return_value
        session_mock.assert_called_with(config_instance)
        os_mock.path.expanduser.assert_has_calls(
            [mock.call('foo'), mock.call('bar'), mock.call('baz')],
            any_order=True)
        os_mock.makedirs.assert_called_with('bar')
        self.assertEqual(config_instance.cache_location, 'foo')
        self.assertEqual(config_instance.settings_location, 'bar')
        config_instance.load_application_key_file.assert_called_with('baz')

    def test_relogin(self, sink_mock, session_mock):
        session_instance = session_mock.return_value
        Spotify(Options())
        session_mock.return_value.relogin.assert_called_with()

    def test_login(self, sink_mock, session_mock):
        session_instance = session_mock.return_value
        service = Spotify(Options())

        session_instance.on.side_effect = (lambda event, f:
            f(session_instance, spotify.ErrorType.OK))
        service.login(username='alice', password='123456')
        session_instance.login.assert_called_with(
            'alice', '123456', remember_me=True)

        session_instance.on.side_effect = (lambda event, f:
            f(session_instance, spotify.ErrorType.BAD_USERNAME_OR_PASSWORD))
        with self.assertRaises(spotify.LibError):
            service.login(username='alice', password='123456')

    def test_connection(self, sink_mock, session_mock):
        service = Spotify(Options())

        states = [
            'Logged out',
            'Logged in',
            'Disconnected',
            'Undefined',
            'Offline'
        ]

        for i, state in enumerate(states):
            session_mock.return_value.connection.state = i
            self.assertEqual(service.connection(), {
                'result': state
            })

    def test_guard(self, sink_mock, session_mock):
        service = Spotify(Options())
        session_mock.return_value.connection.state = 0

        for method in ('next_track', 'prev_track', 'next_set', 'play', 'add'):
            with self.assertRaises(Unauthorized):
                getattr(service, method)()

    # TODO
