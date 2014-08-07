import logging
import os
import random

import spotify
from twisted.internet import defer, reactor
from twisted.web import xmlrpc

import handler

class Choice(object):
    """A list of choices from a Spotify search."""
    def __init__(self, selector):
        """Create an empty choice."""
        self._selector = selector
        self._results = []
        self._index = 0

    @property
    def value(self):
        """The current choice."""
        try:
            return self._results[self._index]
        except IndexError:
            return None

    @defer.inlineCallbacks
    def next(self):
        """Asynchronously go to the next result."""
        self._index += 1
        if self._index >= len(self._results):
            results = yield self._more()
            self._append_results(results)
        if self._index >= len(self._results):
            self._index = len(self._results) - 1

    def prev(self):
        """Asynchronously go to the previous result."""
        if self._index > 0:
            self._index -= 1
        return defer.maybeDeferred(None)

    def _loaded(self, deferred, search):
        try:
            results = list(self._selector(search))
            print results
            if not results:
                raise xmlrpc.Fault(1, 'no results')
        except Exception as e:
            deferred.errback(e)
        else:
            deferredList = handler.wait_all(results)
            deferredList.chainDeferred(deferred)
        return False

    def _append_results(self, results):
        """Append the results of a search."""
        if not results:
            raise xmlrpc.Fault(1, 'no results')
        self._results.extend(results)

    def _more(self):
        """Asynchronously load more results."""
        d = defer.Deferred()

        self._last_search.more(lambda search: choice._loaded(d, search))
        return d

    @classmethod
    def search(cls, session, query, selector, **kwds):
        """Asynchronously load a search."""
        choice = Choice(selector)
        d = defer.Deferred()

        def load_first(results):
            choice._append_results(results)
            return choice

        session.search(query, lambda search: choice._loaded(d, search), **kwds)
        d.addCallback(load_first)
        return d

class Track(object):
    """A single instance of a loaded Spotify track."""
    def __init__(self, track):
        """Create from a loaded spotify track."""
        spotify.Error.maybe_raise(track.error)
        self._track = track

    @property
    def data(self):
        """The backing Spotify track."""
        return self._track

    def encode_response(self):
        return {
            'type': 'Track',
            'name': self._track.name,
            'uri': self._track.link.uri
        }

    @classmethod
    def load(cls, track):
        """Asynchronously load a track's metadata."""
        d = defer.Deferred()
        session = track._session

        def check_loaded(session):
            if track.is_loaded:
                try:
                    result = cls(track)
                except spotify.LibError as e:
                    d.errback(e)
                else:
                    d.callback(result)
                return False

        if not check_loaded(session) is False:
            session.on(spotify.SessionEvent.METADATA_UPDATED, check_loaded)
        return d

class Playlist(object):
    """A loaded, shuffled, and partially-played playlist."""
    def __init__(self, playlist):
        """Create from a loaded Spotify playlist."""
        if not playlist.is_loaded:
            raise spotify.LibError(spotify.ErrorType.IS_LOADING)
        self._playlist = playlist
        # TODO: better shuffle
        self._track_set = [Track(track) for track in playlist.tracks]
        random.shuffle(self._track_set)
        # TODO: tracks added, removed

    @property
    def track_set(self):
        """The current list of tracks."""
        return self._track_set

    def encode_response(self):
        return {
            'type': 'Playlist',
            'name': self._playlist.name,
            'uri': self._playlist.link.uri
        }

    @classmethod
    def load(cls, playlist):
        """Asynchronously load a playlist."""
        if isinstance(playlist, spotify.SearchPlaylist):
            print playlist.name
            playlist = playlist.playlist

        d = defer.Deferred()
        session = playlist._session

        def onTracksLoaded(result):
            print 'tracks loaded!'
            return cls(playlist)

        def check_loaded(session):
            if playlist.is_loaded:
                print 'loaded!'
                tracks = handler.wait_all(
                    [Track.load(track) for track in playlist.tracks])
                tracks.addCallback(onTracksLoaded)
                tracks.chainDeferred(d)

        if not check_loaded(session) is False:
            playlist.on(spotify.PlaylistEvent.PLAYLIST_STATE_CHANGED, check_loaded)
        return d

class Spotify(handler.Handler):
    """Spotify handler.

    Settings:
        log_level
        cache_dir
        data_dir
        key_file
        timeout
        results
    """

    def __init__(self, config):
        name = 'spotify'

        super(Spotify, self).__init__(name, self._spotifyFault)

        options = config.get(name, {})

        if 'log_level' in options:
            logging.getLogger(name).setLevel(options['log_level'])

        spotify_config = spotify.Config()
        if 'cache_dir' in options:
            spotify_config.cache_location = \
                os.path.expanduser(options['cache_dir'])
        if 'data_dir' in options:
            spotify_config.settings_location = \
                os.path.expanduser(options['data_dir'])
        if 'key_file' in options:
            spotify_config.load_application_key_file(
                os.path.expanduser(options['key_file']))

        if not os.path.exists(spotify_config.settings_location):
            os.makedirs(spotify_config.settings_location)

        self._session = spotify.Session(config=spotify_config)

        spotify.AlsaSink(self._session)

        self._pending = None
        self._process_events()

        self._session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, self._notify)
        self._session.on(spotify.SessionEvent.CONNECTION_ERROR, self.pause)
        self._session.on(spotify.SessionEvent.STREAMING_ERROR, self.pause)
        self._session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, self.pause)
        self._session.on(spotify.SessionEvent.END_OF_TRACK, self.next_track)

        self._timeout = int(options.get('timeout', 20))

        # Playback
        self._playing = False
        self._current_track = None
        self._history = []

        # Queues of choices
        self._playlist_queue = []
        self._track_queue = []

        # Search
        self._last_choice = None

    def _spotifyFault(self, failure):
        failure.trap(spotify.LibError)
        e = failure.value
        raise xmlrpc.Fault(int(e.error_type), str(e))

    def _process_events(self):
        """Process spotify events and schedule the next timeout."""
        if self._pending and self._pending.active():
            self._pending.cancel()
        timeout = self._session.process_events() / 1000.0
        self._pending = reactor.callLater(timeout, self._process_events)

    def _notify(self, *args):
        reactor.callFromThread(self._process_events)

    @handler.method
    def login(self, username=None, password=None):
        """Log in to Spotify."""
        d = defer.Deferred()

        def logged_in(session, error_type):
            try:
                spotify.Error.maybe_raise(error_type)
            except spotify.LibError as e:
                d.errback(e)
            else:
                d.callback(None)
            return False

        self._session.on(spotify.SessionEvent.LOGGED_IN, logged_in)

        if username is None:
            self._session.relogin()
        elif password:
            self._session.login(username, password, remember_me=True);
        else:
            raise xmlrpc.Fault(1, "password required")
        handler.setTimeout(d, self._timeout)
        return d

    @handler.method
    def connection_state(self, *args):
        states = {
            0: 'logged out',
            1: 'logged in',
            2: 'disconnected',
            3: 'undefined',
            4: 'offline'
        }
        return states[self._session.connection.state]

    @handler.method
    def paused(self, *args):
        """Returns whether playback is running."""
        return not self._playing

    @handler.method
    def current_track(self, *args):
        """Return the currently playing track."""
        return self._current_track

    @handler.method
    def history(self, *args):
        """Return the track history."""
        return self._history

    @handler.method
    def track_queue(self, *args):
        """Return the current track queue."""
        return [choice.value for choice in self._track_queue]

    @handler.method
    def playlist_queue(self, *args):
        """Return the current playlist queue."""
        return [choice.value for choice in self._playlist_queue]

    @handler.method
    def last_result(self, *args):
        """Return the last choice made."""
        if self._last_choice:
            return self._last_choice.value

    @handler.method
    def lineup(self, *args):
        """Return the next tracks to play."""
        return [choice.value for choice in self._track_queue] + \
            [track for choice in self._playlist_queue
                   for track in choice.value.track_set]

    def _sync_player(self, *args):
        """Load and play the current track, and prefetch the next."""
        lineup = self.lineup()

        try:
            track = lineup[0]
        except IndexError:
            self._session.player.unload()
            self._current_track = None
        else:
            if track is not self._current_track:
                self._session.player.load(track.data)
                self._current_track = track
                self.unpause()

        try:
            next_track = lineup[1]
        except IndexError:
            pass
        else:
            self._session.player.prefetch(next_track.data)

    @handler.method
    def unpause(self, *args):
        """Resume spotify playback."""
        if self._current_track:
            self._playing = True
            self._session.player.play()
        return self._playing

    @handler.method
    def pause(self, *args):
        """Pause spotify playback."""
        self._playing = False
        self._session.player.pause()
        return True

    def _drop_empty_playlists(self):
        queue = self._playlist_queue
        while queue and not queue[0].track_set:
            queue.pop(0)

    @handler.method
    def next_track(self, *args):
        """Load and play the next track."""
        try:
            self._track_queue.pop(0)
        except IndexError:
            self._drop_empty_playlists()
            try:
                self._playlist_queue[0].pop(0)
            except IndexError:
                pass
            self._drop_empty_playlists()

        if self._current_track:
            self._history.insert(0, self._current_track)
        self._sync_player()
        return self._current_track

    @handler.method
    def prev_track(self, *args):
        """Load and play the previous track."""
        if self._history:
            track = self._history.pop(0)
            self._track_queue.insert(0, Choice([track]))
            self._sync_player()
        return self._current_track

    @handler.method
    def next_playlist(self, *args):
        """Load an play the next playlist."""
        try:
            self._playlist_queue.pop(0)
            return self._playlist_queue[0]
        except IndexError:
            pass

    @handler.method
    def restart_track(self, *args):
        """Restart the track."""
        self._session.player.seek(0)
        self.unpause()
        return self._current_track

    @handler.method
    @defer.inlineCallbacks
    def next_result(self, *args):
        """Go to the previous result."""
        if self._last_choice:
            yield self._last_choice.next()
            self._sync_player()
        defer.returnValue(self.last_result())

    @handler.method
    @defer.inlineCallbacks
    def prev_result(self, *args):
        """Go to the next result."""
        if self._last_choice:
            yield self._last_choice.prev()
            self._sync_player()
        defer.returnValue(self.last_result())

    def _search(self, query, **kwds):
        """Asynchronously load a search."""
        d = defer.Deferred()

        def loaded(search):
            try:
                spotify.Error.maybe_raise(search.error)
            except spotify.LibError as e:
                d.errback(e)
            else:
                d.callback(search)
            return False

        self._session.search(query, loaded, **kwds)
        handler.setTimeout(d, self._timeout)
        return d

    @defer.inlineCallbacks
    def _search_tracks(self, query):
        """Asynchronously load a choice of tracks from a search."""
        choice = yield Choice.search(
            self._session,
            query,
            lambda search: [Track.load(track) for track in search.tracks],
            track_count=5,
            album_count=0,
            artist_count=0,
            playlist_count=0)
        # TODO: filter duplicates
        self._last_choice = choice
        defer.returnValue(choice)

    @defer.inlineCallbacks
    def _search_playlists(self, query):
        """Asynchronously load a choice of playlists from a search."""
        choice = yield Choice.search(
            self._session,
            query,
            lambda search: [Playlist.load(playlist)
                for playlist in search.playlists],
            track_count=0,
            album_count=0,
            artist_count=0,
            playlist_count=1)
        # TODO: filter duplicates
        self._last_choice = choice
        defer.returnValue(choice)

    @handler.method
    @defer.inlineCallbacks
    def play_track(self, query):
        """Play a track now."""
        choice = yield self._search_tracks(query)
        self._track_queue[0:1] = [choice]
        self._sync_player()
        defer.returnValue(self.last_result())

    @handler.method
    @defer.inlineCallbacks
    def bump_track(self, query):
        """Play a track next."""
        choice = yield self._search_tracks(query)
        self._track_queue.insert(1, choice)
        self._sync_player()
        defer.returnValue(self.last_result())

    @handler.method
    @defer.inlineCallbacks
    def queue_track(self, query):
        """Place a track at the end of the queue."""
        choice = yield self._search_tracks(query)
        self._track_queue.append(choice)
        self._sync_player()
        defer.returnValue(self.last_result())

    @handler.method
    @defer.inlineCallbacks
    def play_playlist(self, query):
        """Play a playlist now."""
        choice = yield self._search_playlists(query)
        self._playlist_queue[0:1] = [choice]
        self._sync_player()
        defer.returnValue(self.last_result())

    @handler.method
    @defer.inlineCallbacks
    def bump_playlist(self, query):
        """Play a playlist next."""
        choice = yield self._search_playlists(query)
        self._playlist_queue.insert(1, choice)
        self._sync_player()
        defer.returnValue(self.last_result())

    @handler.method
    @defer.inlineCallbacks
    def queue_playlist(self, query):
        """Place a playlist at the end of the queue."""
        choice = yield self._search_playlists(query)
        self._playlist_queue.append(choice)
        self._sync_player()
        defer.returnValue(self.last_result())
