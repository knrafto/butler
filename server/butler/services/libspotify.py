from __future__ import division

import functools
import os
import random
import traceback

import gevent
import gevent.event
import Queue
import spotify
from werkzeug.exceptions import BadGateway, BadRequest, Unauthorized

from butler.options import Options
from butler.routing import endpoint
from butler.service import singleton
from butler.services.player import Metadata, Track, TrackSet

def link_url(link):
    return 'http://open.spotify.com/' + \
        link.uri[len('spotify:'):].replace(':', '/')

def translate_error(error_type):
    exception_types = {
        spotify.ErrorType.BAD_USERNAME_OR_PASSWORD: BadRequest,
        spotify.ErrorType.NETWORK_DISABLED: BadGateway,
        spotify.ErrorType.NO_CREDENTIALS: Unauthorized,
        spotify.ErrorType.NO_STREAM_AVAILABLE: BadGateway,
        spotify.ErrorType.NO_SUCH_USER: BadRequest,
        spotify.ErrorType.OTHER_PERMANENT: BadRequest,
        spotify.ErrorType.OTHER_TRANSIENT: BadRequest,
        spotify.ErrorType.PERMISSION_DENIED: Unauthorized,
        spotify.ErrorType.TRACK_NOT_PLAYABLE: BadRequest,
        spotify.ErrorType.UNABLE_TO_CONTACT_SERVER: BadGateway,
        spotify.ErrorType.USER_BANNED: BadRequest,
        spotify.ErrorType.USER_NEEDS_PREMIUM: BadRequest
    }
    lib_error = spotify.LibError(error_type)
    try:
        exception_type = exception_types[error_type]
    except KeyError:
        return lib_error
    else:
        return exception_type(str(lib_error))

class SpotifyTrack(Track):
    def __init__(self, session, metadata, track):
        super(SpotifyTrack, self).__init__(metadata)
        self._session = session
        self.track = track

    def load(self):
        self._session.player.load(self.track)

    def unload(self):
        self._session.player.unload()

    def prefetch(self):
        self._session.player.prefetch(self.track)

    def play(self, play=True):
        self._session.player.play(play)

    def seek(self, seconds):
        self._session.player.seek(int(seconds * 1000))

class SpotifySearch(object):
    def __init__(self, tracks, albums, artists, playlists):
        self.tracks = list(tracks)
        self.albums = list(albums)
        self.artists = list(artists)
        self.playlists = list(playlists)

    def json(self):
        return {
            'tracks': self.tracks,
            'albums': self.albums,
            'artists': self.artists,
            'playlists': self.playlists
        }

@singleton
class Spotify(object):
    """Spotify plugin.

    This plugin can play tracks and playlists in a queue, and can
    search Spotify.
    """
    name = 'spotify'
    depends = ['options', 'player']

    def __init__(self, options, player):
        options = options.options(self.name)
        self.player = player

        cachedir = options.str('cachedir')
        datadir = options.str('datadir')
        keyfile = options.str('keyfile')
        self._timeout = options.float('timeout')

        config = spotify.Config()
        if cachedir:
            config.cache_location = os.path.expanduser(cachedir)
        if datadir:
            datadir = os.path.expanduser(datadir)
            if not os.path.exists(datadir):
                os.makedirs(datadir)
            config.settings_location = datadir
        if keyfile:
            config.load_application_key_file(os.path.expanduser(keyfile))

        self._session = spotify.Session(config)
        self._session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, self._notify)
        self._session.on(spotify.SessionEvent.CONNECTION_ERROR, self._pause)
        self._session.on(spotify.SessionEvent.STREAMING_ERROR, self._pause)
        self._session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, self._pause)
        self._session.on(spotify.SessionEvent.END_OF_TRACK, self._end_of_track)
        spotify.AlsaSink(self._session)

        self._pending = Queue.Queue()
        self._loading = []

        gevent.spawn(self._process_events)
        self._notify()

        self._session.relogin()

    def _process_events(self):
        """Process events and load resources."""
        while True:
            try:
                self._pending.get(False)
            except Queue.Empty:
                gevent.sleep(0.001) # spin
            else:
                try:
                    timeout = self._session.process_events() / 1000.0
                except Exception:
                    traceback.print_exc()
                gevent.spawn_later(timeout, self._notify)
                self._process_loading()

    def _notify(self, *args):
        """Notify the main thread to process events."""
        self._pending.put(1)

    def _check_status(self, resource):
        error_type = getattr(resource, 'error', spotify.ErrorType.OK)
        if error_type not in (
                spotify.ErrorType.OK,
                spotify.ErrorType.IS_LOADING):
            raise translate_error(error_type)
        return resource.is_loaded

    def _load(self, resource):
        """Block until a resource is loaded."""
        if self._check_status(resource):
            return resource
        result = gevent.event.AsyncResult()
        self._loading.append((resource, result))
        try:
            return result.get()
        finally:
            self._loading.remove((resource, result))

    def _process_loading(self):
        for resource, result in self._loading:
            try:
                if self._check_status(resource):
                    result.set(resource)
            except Exception as e:
                result.set_exception(e)

    def _fetch_track(self, track):
        self._load(track)
        metadata = Metadata(
            id=track.link.uri,
            name=track.name,
            artist=self._load(self._load(track.album).artist).name,
            duration=track.duration / 1000,
            url=link_url(track.link),
            artwork_url=link_url(self._load(track.album).cover_link()),
            backend='spotify')
        return SpotifyTrack(self._session, metadata, track)

    def _fetch_album(self, album, shuffle=False):
        tracks = map(self._fetch_track, self._load(album.browse()).tracks)
        duration = sum(track.metadata.duration for track in tracks)
        self._load(album)
        metadata = Metadata(
            id=album.link.uri,
            name=album.name,
            artist=self._load(album.artist).name,
            duration=duration,
            url=link_url(album.link),
            artwork_url=link_url(album.cover_link()),
            backend='spotify')
        return TrackSet(metadata, tracks, shuffle)

    def _fetch_artist(self, artist, shuffle=False):
        tracks = map(self._fetch_track, self._load(artist.browse()).tracks)
        duration = sum(track.metadata.duration for track in tracks)
        self._load(artist)
        metadata = Metadata(
            id=artist.link.uri,
            name=artist.name,
            artist=artist.name,
            duration=duration,
            url=link_url(artist.link),
            artwork_url=link_url(album.portrait_link()),
            backend='spotify')
        return TrackSet(metadata, tracks, shuffle)

    def _fetch_playlist(self, playlist, shuffle=False):
        self._load(playlist)
        tracks = map(self._fetch_tracks, playlist.tracks)
        duration = sum(track.metadata.duration for track in tracks)
        metadata = Metadata(
            id=playlist.link.uri,
            name=playlist.name,
            artist=self._load(playlist.owner).display_name,
            duration=duration,
            url=link_url(playlist.link),
            artwork_url=link_url(playlist.image()),
            backend='spotify')
        return TrackSet(metadata, tracks, shuffle)

    def _fetch_uri(self, uri, shuffle=False):
        """Fetch a TrackSet from a link."""
        link = self._session.get_link(uri)
        if link.type == spotify.LinkType.TRACK:
            return TrackSet.singleton(self._fetch_track(link.as_track()))
        elif link.type == spotify.LinkType.ALBUM:
            return self._fetch_album(link.as_album(), shuffle)
        elif link.type == spotify.LinkType.ARTIST:
            return self._fetch_artist(link.as_artist(), shuffle)
        elif link.type == spotify.LinkType.PLAYLIST:
            return self._fetch_playlist(link.as_playlist(), shuffle)
        else:
            raise ValueError("Unknown link type for '%s': %r"
                % (uri, link.type))

    def _guard(seld):
        if self._session.connection.state not in (
                spotify.ConnectionState.LOGGED_IN,
                spotify.ConnectionState.OFFLINE):
            raise Unauthorized()

    def _timeout_context(self):
        """Return a context manager that will timeout the current
        operation with a 502: Bad Gateway.
        """
        return gevent.Timeout(self._timeout,
                              BadGateway('Spotify operation timed out'))

    def _pause(self, *args):
        self.player.play(play=False)

    def _end_of_track(self, *args):
        self.player.next_track()

    @endpoint('/login/', methods=['POST'])
    def login(self, **kwds):
        """Log in to Spotify."""
        options = Options(kwds)
        username = options.str('username')
        password = options.str('password')

        result = gevent.event.AsyncResult()

        def logged_in(session, error_type):
            if error_type != spotify.ErrorType.OK:
                result.set_exception(translate_error(error_type))
            else:
                result.set(None)
            return False

        self._session.on(spotify.SessionEvent.LOGGED_IN, logged_in)
        self._session.login(username, password, remember_me=True);

        with self._timeout_context():
            result.get()

    @endpoint('/add/', methods=["POST"])
    def add(self, **kwds):
        """Add a track or set from a link.

        Parameters:
            id/uri/url (required): the Spotify uri/url
            index: the index to insert at
            shuffle: shuffle songs
        """
        self._guard()
        options = Options(kwds)
        uri = options.str('id') or options.str('uri') or options.str('url')
        index = options.int('index')
        shuffle = options.bool('shuffle')
        if not uri:
            raise BadRequest('a uri or url is required')
        with self._timeout_context():
            track_set = self._fetch_uri(uri, shuffle=shuffle)
        self.player.add(index, track_set)

    @endpoint('/search/')
    def search(self, **kwds):
        self._guard()
        result = gevent.event.AsyncResult()

        def search_loaded(search):
            if error_type != spotify.ErrorType.OK:
                result.set_exception(translate_error(error_type))
            else:
                result.set(None)

        try:
            query = kwds.pop('q')
        except KeyError:
            raise BadRequest('a query is required')
        try:
            self._session.search(query, callback=search_loaded, **kwds)
        except TypeError:
            raise BadRequest('bad parameters')
        with self._timeout_context():
            search = result.get()
            tracks = map(self._fetch_track, search.tracks)
            albums = map(self._fetch_album, search.albums)
            artists = map(self._fetch_artist, search.artists)
            playlists = map(
                lambda search_playlist:
                    self._fetch_playlist(search_playlist.playlist),
                search.playlists)
        return SpotifySearch(tracks, albums, artists, playlists)
