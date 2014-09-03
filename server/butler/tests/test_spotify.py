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
    metadata = player.Metadata(
        id='spotify:track:foo',
        name='spam',
        artist='eggs',
        duration=1.0,
        url='http://open.spotify.com/track/foo',
        image_url='http://open.spotify.com/image/foo',
        backend='spotify')
    player = mock.Mock(spec=player.Player)

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

    def _mock_link(self, url):
        link = mock.Mock(spec=spotify.Link)
        link.uri = 'spotify:' + \
            url[len('http://open.spotify.com/')].replace('/', ':')

    def _mock_track(self, metadata):
        artist = mock.Mock(spec=spotify.Artist)
        artist.name = metadata.artist

        album = mock.Mock(spec=spotify.Album)
        album.artist = artist
        album.cover_link.return_value = self._mock_link(metadata.image_url)

        track = mock.Mock(spec=spotify.Track)
        track.link.uri = metadata.id
        track.name = metadata.name
        track.duration = metadata.duration
        return track

    def _mock_album(self, metadata, tracks):
        artist = mock.Mock(spec=spotify.Artist)
        artist.name = metadata.artist

        album = mock.Mock(spec=spotify.Album)
        album.link.uri = metadata.id
        album.name = metadata.name
        album.artist = artist
        album.cover_link.return_value = self._mock_link(metadata.image_url)
        album.browser.return_value.tracks = tracks
        return album

    def _mock_artist(self, metadata, tracks):
        artist = mock.Mock(spec=spotify.Artist)
        artist.link.uri = metadata.id
        artist.name = metadata.name
        artist.portrait_link.return_value = self._mock_link(metadata.image_url)
        artist.browser.return_value.tracks = tracks
        return artist

    def _mock_playlist(self, metadata, tracks):
        playlist = mock.Mock(spec=spotify.Playlist)
        playlist.link.uri = metadata.id
        playlist.name = metadata.name
        playlist.owner.display_name = metadata.artist
        playlist.image.return_value = self._mock_link(metadata.image_url)
        playlist.tracks = tracks
        return playlist
