import unittest
import mock

import gevent

import butler
from servants import libspotify, player

spotify = libspotify.spotify

@mock.patch.object(spotify, 'Session', autospec=True)
@mock.patch.object(spotify, 'AlsaSink', autospec=True)
class SpotifyTestCase(unittest.TestCase):
    metadata = player.Metadata(
        id='spotify:track:foo',
        name='spam',
        artist='eggs',
        duration=1000,
        url='http://open.spotify.com/track/foo',
        image_url='http://open.spotify.com/image/foo',
        backend='spotify')

    def setUp(self):
        self.butler = mock.Mock(spec=butler.Butler)

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

        libspotify.Spotify(self.butler, {
            'cachedir': 'foo',
            'datadir': 'bar',
            'keyfile': 'baz'
        })

        session_mock.assert_called_with(config_mock())
        os_mock.path.expanduser.assert_has_calls(
            [mock.call('foo'), mock.call('bar'), mock.call('baz')],
            any_order=True)
        os_mock.makedirs.assert_called_with('bar')
        self.assertEqual(config_mock().cache_location, 'foo')
        self.assertEqual(config_mock().settings_location, 'bar')
        config_mock().load_application_key_file.assert_called_with('baz')

    def test_relogin(self, sink_mock, session_mock):
        libspotify.Spotify(self.butler, {})
        session_mock().relogin.assert_called_with()

    def test_login(self, sink_mock, session_mock):
        session = session_mock.return_value
        servant = libspotify.Spotify(self.butler, {'timeout': 0})

        session.on.side_effect = (lambda event, f:
            f(session, spotify.ErrorType.OK))
        servant.login('alice', '123456')
        session.login.assert_called_with(
            'alice', '123456', remember_me=True)

        session.on.side_effect = (lambda event, f:
            f(session_mock(), spotify.ErrorType.BAD_USERNAME_OR_PASSWORD))
        with self.assertRaises(spotify.LibError):
            servant.login('alice', '123456')

        session.on.side_effect = None
        session.login.side_effect = (lambda username, password, remember_me:
            gevent.sleep())
        with self.assertRaises(gevent.Timeout):
            servant.login('alice', '123456')

        session.on.side_effect = (lambda event, f:
            f(session_mock(), spotify.ErrorType.UNABLE_TO_CONTACT_SERVER))
        session.login.side_effect = None
        with self.assertRaises(spotify.LibError):
            servant.login('alice', '123456')

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
        track.seek(314)
        session.player.seek.assert_called_with(314)

    def _mock_link(self, url):
        link = mock.Mock(spec=spotify.Link)
        link.uri = 'spotify:' + \
            url[len('http://open.spotify.com/'):].replace('/', ':')
        return link

    def _mock_track(self, metadata):
        image_link = mock.Mock(spec=spotify.Link)
        image_link.uri = 'spotify:' + metadata.image_url[
            len('http://open.spotify.com/'):].replace('/', ':')

        artist = mock.Mock(spec=spotify.Artist)
        artist.loaded = True
        artist.error = spotify.ErrorType.OK
        artist.name = metadata.artist

        album = mock.Mock(spec=spotify.Album)
        album.loaded = True
        album.error = spotify.ErrorType.OK
        album.artist = artist
        album.cover_link.return_value = image_link

        track = mock.Mock(spec=spotify.Track)
        track.loaded = True
        track.error = spotify.ErrorType.OK
        track.link.uri = metadata.id
        track.name = metadata.name
        track.duration = metadata.duration
        track.album = album
        return track

    def _mock_album(self, tracks):
        browser = mock.Mock(spec=spotify.AlbumBrowser)
        browser.loaded = True
        browser.error = spotify.ErrorType.OK
        browser.tracks = tracks

        album = mock.Mock(spec=spotify.Album)
        album.loaded = True
        album.error = spotify.ErrorType.OK
        album.browse.return_value = browser
        return album

    def _mock_artist(self, tracks):
        browser = mock.Mock(spec=spotify.AlbumBrowser)
        browser.loaded = True
        browser.error = spotify.ErrorType.OK
        browser.tracks = tracks

        artist = mock.Mock(spec=spotify.Album)
        artist.loaded = True
        artist.error = spotify.ErrorType.OK
        artist.browse.return_value = browser
        return artist

    def _mock_playlist(self, tracks):
        playlist = mock.Mock(spec=spotify.Playlist)
        playlist.loaded = True
        playlist.error = spotify.ErrorType.OK
        playlist.tracks = tracks
        return playlist

    def test_add(self, sink_mock, session_mock):
        session = session_mock.return_value
        servant = libspotify.Spotify(self.butler, {})
        session.connection.state = 1

        track_metadata = player.Metadata(
            id='spotify:track:foo',
            name='spam',
            artist='eggs',
            duration=1000,
            url='http://open.spotify.com/track/foo',
            image_url='http://open.spotify.com/image/foo',
            backend='spotify')

        tracks = [self._mock_track(track_metadata) for _ in range(6)]

        link = mock.Mock(spec=spotify.Link)
        session.get_link.return_value = link

        link.type = spotify.LinkType.TRACK
        link.as_track.return_value = tracks[0]
        servant.add('foo', index=2, shuffle=True)
        self.butler.call.assert_called_with(
            'player.add',
            2, [libspotify.SpotifyTrack(None, track_metadata, None)], True)

        link.type = spotify.LinkType.ALBUM
        link.as_album.return_value = self._mock_album(tracks)
        servant.add('foo')
        self.butler.call.assert_called_with(
            'player.add',
            0, [libspotify.SpotifyTrack(None, track_metadata, None)] * 6, False)

        link.type = spotify.LinkType.ARTIST
        link.as_artist.return_value = self._mock_artist(tracks)
        servant.add('foo')
        self.butler.call.assert_called_with(
            'player.add',
            0, [libspotify.SpotifyTrack(None, track_metadata, None)] * 6, False)

        link.type = spotify.LinkType.PLAYLIST
        link.as_playlist.return_value = self._mock_playlist(tracks)
        servant.add('foo')
        self.butler.call.assert_called_with(
            'player.add',
            0, [libspotify.SpotifyTrack(None, track_metadata, None)] * 6, False)
