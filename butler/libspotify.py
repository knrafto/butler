import functools
from os import path
import random
import sys

import spotify
from twisted.internet import defer, reactor
from twisted.web import xmlrpc

import handler

class Lazy(object):
    """A object that may be loaded later."""
    def __init__(self, value):
        """Initialize with a Deferred or value."""
        deferred = value
        if not isinstance(value, defer.Deferred):
            deferred = defer.Deferred()
            deferred.callback(value)
        self._deferred = deferred

    def wait(self):
        """Wait for the object to be available."""
        d = defer.Deferred()

        def notify(result):
            d.callback(result)
            return result

        self._deferred.addBoth(notify)
        return d

class Choice(object):
    """A list of lazy choices, wrapping around forever."""
    def __init__(self, choices, index=0):
        self._choices = list(map(Lazy, choices))
        if not self._choices:
            raise ValueError('Empty choice')
        self._seek(index)

    def wait(self):
        """Wait for the current choice to be loaded."""
        return self._choices[self._index].wait()

    def next(self):
        """Go to the previous result."""
        self._seek(self._index + 1)

    def prev(self):
        """Go to the next result."""
        self._seek(self._index - 1)

    def _seek(self, i):
        self._index = i % len(self._choices)

    def __repr__(self):
        """Return a string representation of this Choice."""
        return "Choice(%s, %i)" % (repr(self._choices), self._index)

class Track(object):
    """A single instance of a loaded Spotify track."""
    def __init__(self, track):
        """Create from a loaded spotify track."""
        spotify.Error.maybe_raise(track.error)
        self._track = track

    @property
    def backing_track(self):
        """The backing Spotify track."""
        return self._track

    @classmethod
    def load(cls, track):
        """Asynchronously wait for a track's metadata to be loaded."""
        d = defer.Deferred()
        session = track._session

        def check_loaded(session):
            if track.is_loaded:
                try:
                    result = Track(track)
                except spotify.LibError as e:
                    d.errback(e)
                else:
                    d.callback(result)
                return False

        if not check_loaded(session) is False:
            session.on(spotify.SessionEvent.METADATA_UPDATED, check_loaded)

        handler.setTimeout(d, 5)
        return d

    _props = (
        'offline_status',
        'availability',
        'is_local',
        'is_autolinked',
        'playable',
        'is_placeholder',
        'starred',
        'artists',
        'album',
        'name',
        'duration',
        'popularity',
        'disc',
        'index',
        'link',
        'link_with_offset'
    )

for prop in Track._props:
    def getter(self):
        return getattr(self._track, prop)
    setattr(Track, prop, property(getter))

class Playlist(object):
    """A loaded, shuffled, and partially-played playlist."""
    def __init__(self, playlist):
        """Create from a loaded Spotify playlist."""
        if not playlist.is_loaded:
            raise spotify.LibError(spotify.ErrorType.IS_LOADING)
        self._playlist = playlist
        # TODO: better shuffle
        self._track_set = []
        for track in playlist.tracks:
            self._track_set.append(Lazy(Track.load(track)))
        random.shuffle(self._track_set)
        self._track_set_pos = 0
        # TODO: tracks added, removed

    def current_track(self):
        """Asynchronously wait for the current Spotify track."""
        try:
            lazy = self._track_set[self._track_set_pos]
        except IndexError:
            d = defer.Deferred()
            d.callback(None)
            return d
        else:
            return lazy.wait()

    def advance(self):
        """Advance to the next track."""
        self._track_set_pos += 1

    @classmethod
    def load(cls, playlist):
        """Asynchronously wait for a playlist to be loaded."""
        d = defer.Deferred()
        session = playlist._session

        def check_loaded(session):
            if playlist.is_loaded:
                try:
                    result = Playlist(playlist)
                except spotify.LibError as e:
                    d.errback(e)
                else:
                    d.callback(result)
                return False

        if not check_loaded(session) is False:
            playlist.on(spotify.PlaylistEvent.PLAYLIST_STATE_CHANGED, check_loaded)

        handler.setTimeout(d, 5)
        return d

    _props = (
        'name',
        'owner',
        'description'
    )

for prop in Playlist._props:
    def getter(self):
        return getattr(self._playlist, prop)
    setattr(Track, prop, property(getter))

class Spotify(handler.Handler):
    def __init__(self, name):
        super(Spotify, self).__init__(self._spotifyFault)

        # TODO: lockfiles, better way to get folders
        # TODO: more settings
        config = spotify.Config()
        config.load_application_key_file()
        config.cache_location = path.expanduser(path.join('~', '.cache', name, 'spotify'))
        config.settings_location = path.expanduser(path.join('~', '.' + name, 'spotify'))

        self._session = spotify.Session(config=config)

        # TODO: better (non-blocking) sink
        if sys.platform.startswith('linux'):
            self._sink = spotify.AlsaSink(self._session)
        else:
            self._sink = spotify.PortAudioSink(self._session)

        self._pending = None
        self._process_events()

        self._session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, self._notify)
        self._session.on(spotify.SessionEvent.CONNECTION_ERROR, self.pause)
        self._session.on(spotify.SessionEvent.STREAMING_ERROR, self.pause)
        self._session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, self.pause)
        self._session.on(spotify.SessionEvent.START_PLAYBACK, self.unpause)
        self._session.on(spotify.SessionEvent.STOP_PLAYBACK, self.pause)
        self._session.on(spotify.SessionEvent.END_OF_TRACK, self.next_track)

        # Playback
        self._history = [] # list of Tracks
        self._current_track = None # Track
        self._playing = False

        # Queue
        self._playlist = None # Choice of Deferred Playlists
        self._track_queue = [] # list of Choice of Deferred Tracks

        # Search
        self._last_choice = None # Choice

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
        handler.setTimeout(d, 5)
        return d

    @defer.inlineCallbacks
    def _sync_player(self, *args):
        """Load and play the current track."""
        # TODO: prefetch
        track = None
        if self._track_queue:
            track = yield self._track_queue[0].wait()
        elif self._playlist:
            playlist = yield self._playlist.wait()
            track = yield playlist.current_track()

        if track and track is not self._current_track:
            self._session.player.load(track.backing_track)
            self._current_track = track
            self.unpause()
        elif not track:
            self._session.player.unload()
            self._current_track = None

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
    def unpause(self, *args):
        """Resume spotify playback."""
        if self._current_track:
            self._playing = True
            self._session.player.play()
        # TODO: return track

    @handler.method
    def pause(self, *args):
        """Pause spotify playback."""
        self._playing = False
        self._session.player.pause()
        # TODO: return track

    @handler.method
    def paused(self, *args):
        """Returns whether playback is running."""
        return not self._playing

    @handler.method
    @defer.inlineCallbacks
    def next_track(self, *args):
        """Load and play the next track."""
        if self._track_queue:
            self._track_queue.pop(0)
        elif self._playlist:
            playlist = yield self._playlist.wait()
            playlist.advance()

        if self._current_track:
            self._history.insert(0, self._current_track)
        yield self._sync_player()
        # TODO: return track

    @handler.method
    @defer.inlineCallbacks
    def prev_track(self, *args):
        """Load and play the previous track."""
        if self._history:
            track = self._history.pop(0)
            self._track_queue.insert(0, Choice([track]))
            yield self._sync_player()
        # TODO: return track

    @handler.method
    def restart_track(self, *args):
        """Restart the track."""
        self._session.player.seek(0)
        self.unpause()
        # TODO: return track

    @handler.method
    @defer.inlineCallbacks
    def next_result(self, *args):
        """Go to the previous result."""
        if self._last_choice:
            self._last_choice.next()
            yield self._sync_player()
        # TODO: return track or playlist

    @handler.method
    @defer.inlineCallbacks
    def prev_result(self, *args):
        """Go to the next result."""
        if self._last_choice:
            self._last_choice.prev()
            yield self._sync_player()
        # TODO: return track or playlist

    def _search(self, query):
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

        self._session.search(query, loaded)
        handler.setTimeout(d, 5)
        return d

    @defer.inlineCallbacks
    def _search_tracks(self, query):
        """Asynchronously load a choice of tracks from a search."""
        search = yield self._search(query)
        # TODO: filter duplicates
        # TODO: no results
        choice = Choice(map(Track.load, search.tracks))
        self._last_choice = choice
        defer.returnValue(choice)

    @handler.method
    @defer.inlineCallbacks
    def play_track(self, query):
        """Play a track now."""
        choice = yield self._search_tracks(query)
        self._track_queue[0:1] = [choice]
        yield self._sync_player()

    @handler.method
    @defer.inlineCallbacks
    def bump_track(self, query):
        """Play a track next."""
        choice = yield self._search_tracks(query)
        self._track_queue.insert(1, choice)
        yield self._sync_player()

    @handler.method
    @defer.inlineCallbacks
    def queue_track(self, query):
        """Place a track at the end of the queue."""
        choice = yield self._search_tracks(query)
        self._track_queue.append(choice)
        yield self._sync_player()

    @handler.method
    @defer.inlineCallbacks
    def playlist(self, query):
        """Play from a playlist."""
        search = yield self._search(query)
        # TODO: filter duplicates
        # TODO: no results
        def load(searchPlaylist):
            return Playlist.load(searchPlaylist.playlist)
        choice = Choice(map(load, search.playlists))
        self._last_choice = choice
        self._playlist = choice
        yield self._sync_player()

    # TODO: return queue, playlist, current song
