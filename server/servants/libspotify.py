import os
import random
import traceback

import gevent
import gevent.event
import Queue
import spotify

import butler
from servants import player

def link_url(link):
    return 'http://open.spotify.com/' + \
        link.uri[len('spotify:'):].replace(':', '/')

class SpotifyTrack(player.Track):
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

    def seek(self, ms):
        self._session.player.seek(ms)

class Spotify(butler.Servant):
    """Spotify plugin.

    This plugin can play tracks and playlists in a queue, and can
    search Spotify.
    """
    name = 'spotify'

    def __init__(self, butler, config):
        super(Spotify, self).__init__(butler, config)

        cachedir = config.get('cachedir', None)
        datadir = config.get('datadir', None)
        keyfile = config.get('keyfile', None)
        self._timeout = config.get('timeout', None)

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
            raise spotify.LibError(error_type)
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
        metadata = player.Metadata(
            id=track.link.uri,
            name=track.name,
            artist=self._load(self._load(track.album).artist).name,
            duration=track.duration,
            url=link_url(track.link),
            image_url=link_url(self._load(track.album).cover_link()),
            backend='spotify')
        return SpotifyTrack(self._session, metadata, track)

    def _guard(self):
        if self._session.connection.state not in (
                spotify.ConnectionState.LOGGED_IN,
                spotify.ConnectionState.OFFLINE):
            raise Unauthorized()

    def _pause(self, *args):
        self.call('player.play', False)

    def _end_of_track(self, *args):
        self.call('player.next_track')

    def login(self, username, password):
        """Log in to Spotify."""
        result = gevent.event.AsyncResult()

        def logged_in(session, error_type):
            if error_type != spotify.ErrorType.OK:
                result.set_exception(spotify.LibError(error_type))
            else:
                result.set(None)
            return False

        self._session.on(spotify.SessionEvent.LOGGED_IN, logged_in)
        self._session.login(username, password, remember_me=True);

        with gevent.Timeout(self._timeout):
            result.get()

    def add(self, uri, index=0, shuffle=False):
        """Add a track or set from a link"""
        self._guard()
        if not uri:
            raise ValueError('a uri or url is required')
        with gevent.Timeout(self._timeout):
            link = self._session.get_link(uri)
            if link.type == spotify.LinkType.TRACK:
                tracks = [link.as_track()]
            elif link.type == spotify.LinkType.ALBUM:
                tracks = self._load(link.as_album().browse()).tracks
            elif link.type == spotify.LinkType.ARTIST:
                tracks = self._load(link.as_artist().browse()).tracks
            elif link.type == spotify.LinkType.PLAYLIST:
                tracks = self._load(link.as_playlist()).tracks
            else:
                raise ValueError("Unknown link type for '%s': %r"
                    % (uri, link.type))
            tracks = [self._fetch_track(track) for track in tracks]
        self.call('player.add', index, tracks, shuffle)

    def search(self, query, **kwds):
        self._guard()
        result = gevent.event.AsyncResult()

        def search_loaded(search):
            if search.error != spotify.ErrorType.OK:
                result.set_exception(spotify.LibError(error_type))
            else:
                result.set(search)

        self._session.search(query, callback=search_loaded, **kwds)
        with gevent.Timeout(self._timeout):
            search = result.get()
            return {
                'query': query,
                'tracks': [track.link.uri for track in search.tracks]
            }
