import json
import os
import random
import sys
import traceback

import gevent
import gevent.event
import Queue
import spotify
from werkzeug.exceptions import (
    BadGateway, BadRequest, HTTPException, Unauthorized)
from werkzeug.wrappers import Response

from endpoint import route

class TrackSet(object):
    """A set of tracks to be played."""
    target = None
    tracks = []

    def __init__(self, target, tracks):
        """Create a set from a Spotify object and its tracks."""
        self.target = target
        self.tracks = tracks

    def __iter__(self):
        return self

    def next(self):
        """Return the next track. Raises StopIteration if all tracks
        have been played.
        """
        try:
            return self.tracks.pop(0)
        except IndexError:
            raise StopIteration

    def encode(self):
        """Return a dictionary representation."""
        return {
            'target': self.target,
            'tracks': self.tracks
        }

class DictEncoder(json.JSONEncoder):
    """An encoder that uses a list of properties to serialize an
    object. Takes a dictionary of type: properties.

    >>> class Spam(object):
    ...     def __init__(self, eggs):
    ...         self.eggs = eggs
    ...     @property
    ...     def knights(self): return Knight()
    ...
    >>> class Knight(object):
    ...     pass
    ...
    >>> encoder = DictEncoder({
    ...     Spam: lambda obj: {
    ...         'eggs': obj.eggs,
    ...         'knights': obj.knights
    ...     },
    ...     Knight: lambda obj: "ni"
    ... })
    ...
    >>> encoder.encode(Spam('eggs'))
    '{"knights": "ni", "eggs": "eggs"}'
    """
    def __init__(self, encoders):
        super(DictEncoder, self).__init__()
        self.encoders = encoders

    def default(self, obj):
        try:
            encoder = self.encoders[type(obj)]
        except KeyError:
            return super(DictEncoder, self).default(obj)
        return encoder(obj)

def to_uri(resource):
    return resource.link.uri

encoder = DictEncoder({
    TrackSet: lambda obj: obj.encode(),
    spotify.Track: to_uri,
    spotify.Album: to_uri,
    spotify.Artist: to_uri,
    spotify.Playlist: to_uri,
})

def encode(obj):
    """Encode an object as a Response."""
    return Response(encoder.iterencode(obj), content_type='application/json')

class Spotify(object):
    """Spotify plugin.

    This plugin can play tracks and playlists in a queue, and can
    search Spotify.
    """
    plugin_name = 'spotify'

    def __init__(self, cachedir=None, datadir=None, keyfile=None, timeout=30, **kwds):
        config = spotify.Config()
        if cachedir:
            config.cache_location = os.path.expanduser(cachedir)
        if datadir:
            config.settings_location = os.path.expanduser(datadir)
        if keyfile:
            config.load_application_key_file(os.path.expanduser(keyfile))

        if not os.path.exists(config.settings_location):
            os.makedirs(config.settings_location)

        self._session = spotify.Session(config)

        spotify.AlsaSink(self._session)

        self._pending = Queue.Queue()
        gevent.spawn(self._process_events)
        self._notify()

        self._loading = []

        self._session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, self._notify)
        self._session.on(spotify.SessionEvent.CONNECTION_ERROR, self._pause)
        self._session.on(spotify.SessionEvent.STREAMING_ERROR, self._pause)
        self._session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, self._pause)
        self._session.on(spotify.SessionEvent.END_OF_TRACK, self._end_of_track)

        self._timeout = timeout

        # Playback
        self._playing = False
        self._current_track = None
        self._history = []
        self._queue = []

        self._player_state_changed = gevent.event.Event()

        # Relogin
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
                self._check_loaded()
                gevent.spawn_later(timeout, self._notify)

    def _notify(self, *args):
        """Notify the main thread to process events."""
        self._pending.put(1)

    def _pause(self, *args):
        """Pause playback."""
        self._playing = False
        self._session.player.pause()

    def _end_of_track(self, session):
        """Play the next track."""
        self.next_track(None)

    def _guard(self):
        """Ensure the user is logged in."""
        if self._session.connection.state not in (
            spotify.ConnectionState.LOGGED_IN,
            spotify.ConnectionState.OFFLINE
        ):
            raise Unauthorized()

    def _timeout_context(self):
        """Return a context manager that will timeout the current
        operation with a 502: Bad Gateway.
        """
        return gevent.Timeout(
            self._timeout,
            BadGateway('Spotify operation timed out')
        )

    def _fetch(self, uri):
        """Fetch a resource from a link."""
        link = self._session.get_link(uri)
        if link.type == spotify.LinkType.TRACK:
            return link.as_track()
        elif link.type == spotify.LinkType.ALBUM:
            return link.as_album()
        elif link.type == spotify.LinkType.ARTIST:
            return link.as_artist()
        elif link.type == spotify.LinkType.PLAYLIST:
            return link.as_playlist()
        else:
            raise ValueError("Unknown link type for '%s': %r"
                % (uri, link.type))

    def _check_error(self, resource):
        """Check the error of a resource."""
        error_type = getattr(resource, 'error', spotify.ErrorType.OK)
        spotify.Error.maybe_raise(
            error_type, ignores=[spotify.ErrorType.IS_LOADING])

    def _check_loaded(self):
        """Check if resources are loaded."""
        for result, resource in self._loading:
            if resources.is_loaded:
                result.set(resource)
            else:
                try:
                    self._check_error(resources)
                except spotify.LibError as e:
                    result.set_exception(e)

    def _load(self, resource):
        """Block until a resource is loaded."""
        self._check_error(resource)
        if resource.is_loaded:
            return resource

        result = gevent.event.AsyncResult()
        self._loading.append((resource, result))
        try:
            return result.get()
        finally:
            self._loading.remove((resource, result))

    def _load_all(self, resource):
        """Load a resource and everything it references."""
        self._load(resource)
        if isinstance(resource, spotify.Track):
            for artist in resource.artists:
                self._load_all(artist)
            self._load_all(resource.album)
        elif isinstance(resource, spotify.Album):
            self._load_all(resource.artist)
        elif isinstance(resource, spotify.Playlist):
            for track in resource.tracks:
                self._load_all(track)
            self._load_all(resource.owner)

    def _tracks(self, resource):
        """Get tracks for a loaded resource."""
        self._load_all(resource)
        if isinstance(resource, spotify.Track):
            tracks = [resource]
        elif isinstance(resource, (spotify.Album, spotify.Artist)):
            tracks = self._load(resource.browse()).tracks
            for track in resource.tracks:
                self._load(track)
        elif isinstance(resource, spotify.Playlist):
            tracks = resource.tracks
        else:
            raise TypeError("Cannot load tracks from '%s' object"
                % type(resource).__name__)
        return TrackSet(resource, tracks)

    def _sync_player(self):
        """Load and play the current track, and prefetch the next."""
        lineup = [
            track
                for track_set in self._queue
                for track in track_set.tracks
        ]

        try:
            track = lineup[0]
        except IndexError:
            self._current_track = None
            self._session.player.unload()
            self._playing = False
        else:
            self._current_track = track
            self._session.player.load(track)
            self._playing = True
            self._session.player.play()

        try:
            next_track = lineup[1]
        except IndexError:
            pass
        else:
            self._session.player.prefetch(next_track)

        self._player_state_changed.set()
        self._player_state_changed = gevent.event.Event()

    def _insert(self, track_set, where='start'):
        """Insert a track set at a position."""
        prev_head = self._queue[0] if self._queue else None

        if where is None:
            where = 'start'

        if isinstance(where, int):
            self._queue.insert(where, track_set)
        if where == 'start':
            self._queue[0:1] = [track_set]
        elif where == 'next':
            self._queue.insert(1, track_set)
        elif where == 'later':
            index = next(
                (i for i, s in enumerate(self._queue)
                    if type(s.target) is not spotify.Track),
                -1
            )
            self._queue.insert(index, track_set)
        elif when == 'end':
            self._queue.append(track_set)
        else:
            raise ValueError('Unknown ')

        head = self._queue[0] if self._queue else None
        if head is not prev_head:
            self._sync_player()

    # @public
    # def login(self, username, password):
    #     """Log in to Spotify."""
    #     result = gevent.event.AsyncResult()

    #     def logged_in(session, error_type):
    #         try:
    #             spotify.Error.maybe_raise(error_type)
    #         except spotify.LibError as e:
    #             result.set_exception(e)
    #         else:
    #             result.set(None)
    #         return False

    #     self._session.on(spotify.SessionEvent.LOGGED_IN, logged_in)
    #     self._session.login(username, password, remember_me=True);

    #     result.get(self._timeout)

    @route('/connection/')
    def connection(self, request):
        states = [
            'Logged out',
            'Logged in',
            'Disconnected',
            'Undefined',
            'Offline'
        ]
        return encode({
            'result': states[self._session.connection.state]
        })

    @route('/state/')
    def player_state(self, request):
        """Return the current player state."""
        return encode({
            'paused': not self._playing,
            'current_track': self._current_track,
            'history': self._history,
            'queue': self._queue
        })

    @route('/state/push/')
    def push_player_state(self, request):
        """Block until the track changes."""
        self._player_state_changed.wait()
        return self.player_state(request)

    @route('/player/next_track/', methods=["POST"])
    def next_track(self, request):
        """Load and play the next track."""
        self._guard()
        while True:
            if not self._queue:
                break
            try:
                self._queue[0].advance()
            except StopIteration:
                self._queue.pop(0)
            else:
                break

        if self._current_track:
            self._history.insert(0, self._current_track)
        self._sync_player()
        return Response()

    @route('/player/prev_track/', methods=["POST"])
    def prev_track(self, request):
        """Load and play the previous track."""
        self._guard()
        try:
            track = self._history.pop(0)
        except IndexError:
            pass
        else:
            self._queue.insert(0, TrackSet(track))
            self._sync_player()
        return Response()

    @route('/player/next_set/', methods=["POST"])
    def next_set(self, request):
        """Load and play the next track set."""
        self._guard()
        try:
            self._queue.pop(0)
        except IndexError:
            pass
        else:
            self._sync_player()
        return Response()

    @route('/player/play/', methods=["POST"])
    def play(self, request):
        """Resume spotify playback.

        Parameters:
            pause : If present, pause playback
            seek (default: None): Seek position, in milliseconds
        """
        pause = 'pause' in request.form
        ms = request.form.get('seek', type=int)
        if ms:
            self._session.player.seek(ms)
        if not pause and self._current_track:
            self._playing = True
            self._session.player.play()
        elif pause:
            self._playing = False
            self._session.player.pause()
        return Response()

    @route('/player/add/', methods=["POST"])
    def add(self, request):
        """Add a track or set from a link.

        Parameters:
            uri/url: the Spotify uri/url
            where (default: 'start'): one of 'start', 'next', 'later', 'end',
                or an index
        """
        self._guard()
        uri = request.form.get('uri') or request.form.get('url')
        when = request.form.get('where')
        try:
            with self._timeout_context():
                resource = self._fetch(uri)
                track_set = self._tracks(resource)
            self._insert(track_set, when)
        except HTTPException:
            raise
        except Exception as e:
            raise BadRequest(str(e))
        return Response()
