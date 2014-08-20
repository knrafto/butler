import functools
import os
import random
import traceback

import gevent
import gevent.event
import Queue
import spotify
from werkzeug.exceptions import BadGateway, Unauthorized

from butler.options import Options
from butler.routing import endpoint
from butler.service import singleton
from butler.utils import Counter

def translate_spotify_error(f):
    @functools.wraps(f)
    def decorator(*args, **kwds):
        try:
            return f(*args, **kwds)
        except spotify.LibError as e:
            raise # TODO
    return decorator

class Track:
    """A single instance of a track."""
    def __init__(self, track):
        self.data = track

    def json(self):
        return self.data.link.uri

class TrackSet:
    """A set of tracks to be played."""
    target = None
    tracks = []

    def __init__(self, target, tracks, shuffle=False):
        """Create a set from a Spotify object and its tracks."""
        self.target = target
        self.tracks = tracks
        if shuffle:
            random.shuffle(self.tracks)

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

    def json(self):
        """Return a dictionary representation."""
        return {
            'target': self.target,
            'tracks': self.tracks
        }

@singleton
class Spotify(object):
    """Spotify plugin.

    This plugin can play tracks and playlists in a queue, and can
    search Spotify.
    """
    name = 'spotify'
    depends = ['options']

    def __init__(self, options):
        options = options.options(self.name)

        cachedir = options.path('cachedir')
        datadir = options.path('datadir')
        keyfile = options.path('keyfile')
        self._timeout = options.number('timeout')

        config = spotify.Config()
        if cachedir:
            config.cache_location = os.path.expanduser(cachedir)
        if datadir:
            config.settings_location = os.path.expanduser(datadir)
        if keyfile:
            config.load_application_key_file(os.path.expanduser(keyfile))

        if config.settings_location and \
                not os.path.exists(config.settings_location):
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

        # Playback
        self._playing = False
        self._current_track = None
        self._history = []
        self._queue = []

        self._state_counter = Counter()

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

    def _guard(self):
        """Ensure the user is logged in."""
        if self._session.connection.state not in (
                spotify.ConnectionState.LOGGED_IN,
                spotify.ConnectionState.OFFLINE):
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
        for resource, result in self._loading:
            if resource.is_loaded:
                result.set(resource)
            else:
                try:
                    self._check_error(resource)
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

    def _load_tracks(self, resource):
        """Get tracks for a resource."""
        if isinstance(resource, spotify.Track):
            tracks = [resource]
        elif isinstance(resource, (spotify.Album, spotify.Artist)):
            tracks = self._load(resource.browse()).tracks
        elif isinstance(resource, spotify.Playlist):
            self._load(resource)
            tracks = resource.tracks
        else:
            raise TypeError("Cannot load tracks from '%s' object"
                % type(resource).__name__)
        return [Track(self._load(track)) for track in tracks]

    def _sync_player(self):
        """Load and play the current track, and prefetch the next."""
        lineup = [track for track_set in self._queue
            for track in track_set.tracks]

        try:
            track = lineup[0]
        except IndexError:
            track = None
        if track:
            self._session.player.load(track.data)
            self._playing = True
            self._session.player.play()
        else:
            self._session.player.unload()
            self._playing = False

        try:
            next_track = lineup[1]
        except IndexError:
            pass
        else:
            self._session.player.prefetch(next_track.data)

        self._current_track = track
        self._state_counter.set()

    def _pause(self, *args):
        """Pause playback."""
        self._playing = False
        self._session.player.pause()

    def _end_of_track(self, session):
        """Play the next track."""
        self.next_track()

    def _insert(self, track_set, where='start'):
        """Insert a track set at a position."""
        prev_head = self._queue[0] if self._queue else None

        if isinstance(where, int):
            self._queue.insert(where, track_set)
        elif where == 'start':
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
        elif where == 'end':
            self._queue.append(track_set)

        head = self._queue[0] if self._queue else None
        if head is not prev_head:
            self._sync_player()

    @endpoint('/login/', methods=['POST'])
    @translate_spotify_error
    def login(self, **kwds):
        """Log in to Spotify."""
        options = Options(kwds)
        username = options.str('username')
        password = options.str('password')

        result = gevent.event.AsyncResult()

        def logged_in(session, error_type):
            try:
                spotify.Error.maybe_raise(error_type)
            except spotify.LibError as e:
                result.set_exception(e)
            else:
                result.set(None)
            return False

        self._session.on(spotify.SessionEvent.LOGGED_IN, logged_in)
        self._session.login(username, password, remember_me=True);

        with self._timeout_context():
            result.get()

    @endpoint('/connection/')
    @translate_spotify_error
    def connection(self, **kwds):
        """Return the connection state."""
        states = [
            'Logged out',
            'Logged in',
            'Disconnected',
            'Undefined',
            'Offline'
        ]
        return {
            'result': states[self._session.connection.state]
        }

    @endpoint('/state/')
    @translate_spotify_error
    def player_state(self, **kwds):
        """Return the current player state."""
        value = Options(kwds).int('value', None)
        value = self._state_counter.wait(value)
        return {
            'paused': not self._playing,
            'current_track': self._current_track,
            'history': self._history,
            'queue': self._queue,
            'state': value
        }

    @endpoint('/next_track/', methods=["POST"])
    @translate_spotify_error
    def next_track(self, **kwds):
        """Load and play the next track."""
        self._guard()
        while self._queue:
            try:
                self._queue[0].next()
            except StopIteration:
                self._queue.pop(0)
            else:
                break

        if self._current_track:
            self._history.insert(0, self._current_track)
        self._sync_player()

    @endpoint('/prev_track/', methods=["POST"])
    @translate_spotify_error
    def prev_track(self, **kwds):
        """Load and play the previous track."""
        self._guard()
        try:
            track = self._history.pop(0)
        except IndexError:
            pass
        else:
            self._queue.insert(0, TrackSet(track, [track]))
            self._sync_player()

    @endpoint('/next_set/', methods=["POST"])
    @translate_spotify_error
    def next_set(self, **kwds):
        """Load and play the next track set."""
        self._guard()
        try:
            self._queue.pop(0)
        except IndexError:
            pass
        else:
            self._sync_player()

    @endpoint('/playback/', methods=["POST"])
    @translate_spotify_error
    def play(self, **kwds):
        """Resume spotify playback.

        Parameters:
            pause: If present, pause playback
            seek: Seek position, in milliseconds
        """
        options = Options(kwds)
        seek = options.int('seek', None)
        pause = options.bool('pause')
        if seek is not None:
            self._session.player.seek(seek)
        if pause and self._current_track:
            self._playing = True
            self._session.player.play()
        elif pause:
            self._playing = False
            self._session.player.pause()

    @endpoint('/add/', methods=["POST"])
    @translate_spotify_error
    def add(self, **kwds):
        """Add a track or set from a link.

        Parameters:
            uri/url (required): the Spotify uri/url
            where: one of 'start', 'next', 'later', 'end',
                or an index
            shuffle: shuffle songs
        """
        self._guard()
        options = Options(kwds)
        uri = options.str('uri') or options.str('url')
        where = options.str('where') or options.int('where')
        shuffle = options.bool('shuffle')
        if not uri:
            pass # TODO
        with self._timeout_context():
            resource = self._fetch(uri)
            tracks = self._load_tracks(resource)
            track_set = TrackSet(resource, tracks, shuffle=shuffle)
        self._insert(track_set, where)
