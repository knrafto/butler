import functools
from os import path
import sys

import spotify
from twisted.internet import defer, reactor
from twisted.web import xmlrpc

import handler

def spotifyFault(e):
    if not isinstance(e, spotify.LibError):
        e = spotify.LibError(e)
    return xmlrpc.Fault(int(e.error_type), str(e))

def respond(deferred, value, error_type):
    if error_type == spotify.ErrorType.OK:
        deferred.callback(value)
    else:
        deferred.errback(spotifyFault(error_type))

def faultOnError(f):
    @functools.wraps(f)
    def g(*args, **kwds):
        try:
            return f(*args, **kwds)
        except spotify.LibError as e:
            raise spotifyFault(e)
    return g

class Cursor:
    """A position in a list of choices."""
    def __init__(self, choices, index=None):
        self._choices = list(choices)
        if index is not None:
            self._index = index
        else:
            self._index = 0

    @property
    def value(self):
        """The current value, or None if we've walked off the end."""
        try:
            return self._choices[self._index]
        except IndexError:
            return None

    def next(self):
        """Go to the previous result."""
        self._index += 1 # TODO: wrong wraparound behavior
        return self.value

    def prev(self):
        """Go to the next result."""
        self._index -= 1
        return self.value

    def __repr__(self):
        return "Cursor(%s, %i)" % (repr(self._choices), self._index)

class TrackSet(Cursor):
    """A shuffled and partially-played playlist."""
    def __init__(self, playlist):
        self._playlist = playlist
        # TODO: better shuffle
        super(Cursor, self).__init__(shuffle(playlist.tracks))

    @property
    def playlist(self):
        """The backing playlist."""
        return self._playlist

class Spotify(handler.Handler):
    def __init__(self, name):
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
        self._session.on(spotify.SessionEvent.STOP_PLAYBACK, self.unpause)
        self._session.on(spotify.SessionEvent.END_OF_TRACK, self.next_track)

        # Playback
        self._history = [] # list of Tracks
        self._current_track = None # Track
        self._playing = False

        # Queue
        self._playlist = None # Cursor of TrackSets
        self._track_queue = [] # List of Cursors of Tracks

        # Search
        self._last_choice = None # Cursor

    def _process_events(self):
        """Process spotify events and schedule the next timeout."""
        if self._pending and self._pending.active():
            self._pending.cancel()
        timeout = self._session.process_events() / 1000.0
        self._pending = reactor.callLater(timeout, self._process_events)

    def _notify(self, *args):
        reactor.callFromThread(self._process_events)

    @handler.method
    @faultOnError
    def login(self, username=None, password=None):
        """Log in to Spotify."""
        d = defer.Deferred()
        def logged_in(session, error_type):
            respond(d, True, error_type)
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

    def _sync_player(self, *args):
        """Load and play the current track."""
        # TODO: prefetch
        track = None
        if self._track_queue:
            track = self._track_queue[0].value
        elif self._playlist:
            track = self._playlist.value.value

        if track and track != self._current_track:
            self._session.player.load(track)

        self._current_track = track
        if track and self._playing:
            self.unpause()
        else:
            self._playing = False
            self.pause()

    @handler.method
    def unpause(self, *args):
        """Resume spotify playback."""
        if self._current_track:
            self._playing = True
            self._session.player.play()
        return True
        # TODO: return track

    @handler.method
    def pause(self, *args):
        """Pause spotify playback."""
        self._playing = False
        self._session.player.pause()
        return True
        # TODO: return track

    @handler.method
    def next_track(self, *args):
        """Load and play the next track."""
        last_track = None
        if self._track_queue:
            last_track = self._track_queue.pop(0).value
        elif self._playlist:
            last_track = self._playlist.value.value
            self._playlist.value.next()

        if last_track:
            self._history.insert(0, last_track)
        self._sync_player()
        self.unpause()
        return True
        # TODO: return track

    @handler.method
    def prev_track(self, *args):
        """Load and play the previous track."""
        if self._history:
            track = self._history.pop(0)
            self._track_queue.insert(0, Cursor([track]))
            self._sync_player()
            self.unpause()
        return True
        # TODO: return track

    @handler.method
    def restart_track(self, *args):
        """Restart the track."""
        self._session.player.seek(0)
        self.unpause()
        return True
        # TODO: return track

    @handler.method
    def next_result(self, *args):
        """Go to the previous result."""
        if self._last_choice:
            self._last_choice.next()
            self._sync_player()
        return True
        # TODO: return track or playlist

    @handler.method
    def prev_result(self, *args):
        """Go to the next result."""
        if self._last_choice:
            self._last_choice.prev()
            self._sync_player()
        return True
        # TODO: return track or playlist

    def _search(self, query):
        """Asynchronously load a search."""
        d = defer.Deferred()
        def loaded(search):
            respond(d, search, search.error)
            return False
        self._session.search(query, loaded)
        handler.setTimeout(d, 5)
        return d

    @defer.inlineCallbacks
    def _search_tracks(self, query):
        """Asynchronously load a cursor of tracks from a search."""
        search = yield self._search(query)
        self._last_choice = Cursor(search.tracks)
        defer.returnValue(self._last_choice)

    @handler.method
    @defer.inlineCallbacks
    def play_track(self, query):
        """Play a track now."""
        yield self.bump_track(query)
        self.next_track()
        defer.returnValue(True)

    @handler.method
    @defer.inlineCallbacks
    def bump_track(self, query):
        """Play a track next."""
        cursor = yield self._search_tracks(query)
        self._track_queue.insert(1, cursor)
        self._sync_player()
        defer.returnValue(True)

    @handler.method
    @defer.inlineCallbacks
    def queue_track(self, query):
        """Place a track at the end of the queue."""
        cursor = yield self._search_tracks(query)
        self._track_queue.append(cursor)
        self._sync_player()
        defer.returnValue(True)
