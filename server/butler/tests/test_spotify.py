import unittest
import mock

import gevent
from werkzeug.exceptions import BadRequest, BadGateway, Unauthorized

from butler.options import Options
from butler.services import libspotify
from butler.services.libspotify import Spotify
from butler.services import player

spotify = libspotify.spotify

@mock.patch.object(spotify, 'Session', autospec=True)
@mock.patch.object(spotify, 'AlsaSink', autospec=True)
class SpotifyTestCase(unittest.TestCase):
    player = mock.Mock(spec=player.Player)
    data = {
        'id': 'foo',
        'name': 'spam',
        'artist': 'eggs',
        'duration': 1.0,
        'url': 'http://www.foo.org/123',
        'artwork_url': 'http://www.foo.org/123/artwork.jpg',
        'backend': 'spotify'
    }

    def test_link_url(self, sink_mock, session_mock):
        link = mock.Mock(spec=spotify.Link)
        link.uri = 'spotify:type:spamandeggs'
        self.assertEqual(
            libspotify.link_url(link),
            'http://open.spotify.com/type/spamandeggs')

    @mock.patch.object(spotify, 'Config', autospec=True)
    @mock.patch.object(libspotify, 'os', autospec=True)
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
        }), self.player)

        session_mock.assert_called_with(config_mock())
        os_mock.path.expanduser.assert_has_calls(
            [mock.call('foo'), mock.call('bar'), mock.call('baz')],
            any_order=True)
        os_mock.makedirs.assert_called_with('bar')
        self.assertEqual(config_mock().cache_location, 'foo')
        self.assertEqual(config_mock().settings_location, 'bar')
        config_mock().load_application_key_file.assert_called_with('baz')

    def test_relogin(self, sink_mock, session_mock):
        Spotify(Options(), self.player)
        session_mock().relogin.assert_called_with()

    def test_login(self, sink_mock, session_mock):
        session = session_mock.return_value
        service = Spotify(Options({
            'spotify': {
                'timeout': 0
            }
        }), self.player)

        session.on.side_effect = (lambda event, f:
            f(session, spotify.ErrorType.OK))
        service.login(username='alice', password='123456')
        session.login.assert_called_with(
            'alice', '123456', remember_me=True)

        session.on.side_effect = (lambda event, f:
            f(session_mock(), spotify.ErrorType.BAD_USERNAME_OR_PASSWORD))
        with self.assertRaises(BadRequest):
            service.login(username='alice', password='123456')

        session.on.side_effect = None
        session.login.side_effect = (lambda username, password, remember_me:
            gevent.sleep())
        with self.assertRaises(BadGateway):
            service.login(username='alice', password='123456')

        session.on.side_effect = (lambda event, f:
            f(session_mock(), spotify.ErrorType.UNABLE_TO_CONTACT_SERVER))
        session.login.side_effect = None
        with self.assertRaises(BadGateway):
            service.login(username='alice', password='123456')

    def test_track(self, sink_mock, session_mock):
        session = session_mock.return_value
        spotify_track = mock.Mock(spec=spotify.Track)
        metadata = mock.Mock(spec=player.Metadata)
        track = libspotify.SpotifyTrack(session, metadata, spotify_track)

        self.assertEqual(track.metadata, metadata)

        track.load()
        session.player.load.assert_called_with(spotify_track)
        track.unload()
        session.player.unload.assert_called_with()
        track.prefetch()
        session.player.prefetch.assert_called_with(spotify_track)
        track.play(True)
        session.player.play.assert_called_with(True)
        track.seek(2.3456)
        session.player.seek.assert_called_with(2345)

    def _mock_tracks(self, prefix):
        for i in range(3):
            track = mock.Mock(spec=spotify.Track)
            track.is_loaded = True
            track.error = spotify.ErrorType.OK
            track.link.uri = '%strack%i' % (prefix, i + 1)
            yield track

    def _mock_link(self, uri):
        link = mock.Mock(spec=spotify.Link)
        link.uri = uri
        tracks = list(self._mock_tracks(uri))
        if uri.startswith('track'):
            track = mock.Mock(spec=spotify.Track)
            track.is_loaded = True
            track.error = spotify.ErrorType.OK
            track.link = link
            link.type = spotify.LinkType.TRACK
            link.as_track.return_value = track
        elif uri.startswith('album'):
            browser = mock.Mock(spec=spotify.AlbumBrowser)
            browser.is_loaded = True
            browser.error = spotify.ErrorType.OK
            browser.tracks = tracks
            album = mock.Mock(spec=spotify.Album)
            album.is_loaded = True
            album.browse.return_value = browser
            link.type = spotify.LinkType.ALBUM
            link.as_album.return_value = album
        elif uri.startswith('artist'):
            browser = mock.Mock(spec=spotify.ArtistBrowser)
            browser.is_loaded = True
            browser.error = spotify.ErrorType.OK
            browser.tracks = tracks
            artist = mock.Mock(spec=spotify.Artist)
            artist.is_loaded = True
            artist.browse.return_value = browser
            link.type = spotify.LinkType.ARTIST
            link.as_artist.return_value = artist
        elif uri.startswith('playlist'):
            playlist = mock.Mock(spec=spotify.Playlist)
            playlist.is_loaded = True
            playlist.error = spotify.ErrorType.OK
            playlist.tracks = tracks
            link.type = spotify.LinkType.PLAYLIST
            link.as_playlist.return_value = playlist
        return link

    def test_connection(self, sink_mock, session_mock):
        service = Spotify(Options(), self.player)

        states = [
            'Logged out',
            'Logged in',
            'Disconnected',
            'Undefined',
            'Offline'
        ]

        for i, state in enumerate(states):
            session_mock.return_value.connection.state = i
            self.assertEqual(service.connection()['result'], state)

    def test_add(self, sink_mock, session_mock):

        session = session_mock.return_value
        service = Spotify(Options({
            'spotify': {
                'timeout': 0
            }
        }), self.player)

        session.connection.state = 0
        with self.assertRaises(Unauthorized):
            service.add(url='spam')

        session.connection.state = 1
        with self.assertRaises(BadRequest):
            service.add()

        session.get_link.side_effect = lambda link: gevent.sleep(0.005)
        with self.assertRaises(BadGateway):
            service.add(url='spam')

        session.get_link.side_effect = self._mock_link
        service.add(url='track1')
        track_set = self.player.add.mock_calls[0][1]
        self.assertEqual(len(track_set.tracks), 1)
        track = track_set.tracks[0]
        self.assertEqual(track.metadata, Metadata(**self.data))
