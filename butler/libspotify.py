from __future__ import print_function

import os
import random
import sys

import gevent
import gevent.event
import Queue
import spotify
from tinyrpc.dispatch import public

def as_dict(value):
    try:
        f = value.as_dict
    except AttributeError:
        return value
    else:
        return f()

class Search(object):
    """A list of items from a Spotify search."""
    def __init__(self, session, items, **kwds):
        self._session = session
        self._kwds = kwds

        if not items:
            raise Exception('No more results')

        self._items = items
        self._index = 0

    @property
    def value(self):
        try:
            return self._items[self._index]
        except IndexError:
            raise Exception('No more results')

    def next(self):
        self._index += 1
        while self._index >= len(self._items):
            self._kwds['offset'] = len(self._items)
            items = self._fetch_results(self._session, **self._kwds)
            if not items:
                raise Exception('No more results')
            self._items.extend(items)

    def prev(self):
        if self._index > 0:
            self._index -= 1

    def as_dict(self):
        return as_dict(self.value)

    @staticmethod
    def _fetch_results(session, query='', search_type='', offset=0, stride=None):
        result = gevent.event.AsyncResult()

        kwds = {}
        for arg_type in ('track', 'album', 'artist', 'playlist'):
            if arg_type == search_type:
                kwds[arg_type + '_offset'] = offset
                if stride:
                    kwds[arg_type + '_count'] = stride
            else:
                kwds[arg_type + '_offset'] = 0
                kwds[arg_type + '_count'] = 0

        def loaded(search):
            try:
                spotify.Error.maybe_raise(search.error)
            except spotify.LibError as e:
                result.set_exception(e)
            else:
                result.set(search)

        session.search(query, loaded, **kwds)

        ctors = {
            'track': Track.load,
            'playlist': Playlist.load
        }

        search = result.get()
        ctor = ctors[search_type]
        raw_items = getattr(search, search_type + 's')
        return gevent.pool.Pool().map(ctor, raw_items)

    @classmethod
    def load(cls, session, **kwds):
        items = cls._fetch_results(session, **kwds)
        return cls(session, items, **kwds)

class Single(object):
    def __init__(self, value):
        self.value = value

class Track(object):
    def __init__(self, track):
        self.track = track

    @property
    def data(self):
        return self.track

    def as_dict(self):
        return {
            'type': 'Track',
            'name': self.track.name,
            'uri': self.track.link.uri
        }

    @classmethod
    def load(cls, track):
        session = track._session
        result = gevent.event.AsyncResult()

        def loaded():
            if not track.is_loaded:
                return False

            try:
                spotify.Error.maybe_raise(track.error)
            except spotify.LibError as e:
                result.set_exception(e)
            else:
                result.set(None)
            return True

        def check_loaded(session):
            if loaded():
                return False

        if not loaded():
            session.on(spotify.SessionEvent.METADATA_UPDATED, check_loaded)

        result.get()
        return cls(track)

class Playlist(object):
    def __init__(self, playlist, tracks):
        self.playlist = playlist

        self.track_set = tracks
        random.shuffle(self.track_set)

    def next(self):
        try:
            self.track_set.pop(0)
        except IndexError:
            pass

    def as_dict(self):
        return {
            'type': 'Playlist',
            'name': self.playlist.name,
            'uri': self.playlist.link.uri
        }

    @classmethod
    def load(cls, playlist):
        if isinstance(playlist, spotify.SearchPlaylist):
            playlist = playlist.playlist
        result = gevent.event.AsyncResult()

        def loaded():
            if not playlist.is_loaded:
                return False

            result.set()
            return True

        def check_loaded(playlist):
            if loaded():
                return False

        if not loaded():
            playlist.on(spotify.PlaylistEvent.PLAYLIST_STATE_CHANGED, check_loaded)
        # TODO: tracks added, removed

        result.get()
        tracks = gevent.pool.Pool().map(Track.load, playlist.tracks)
        return cls(playlist, tracks)

class Spotify(object):
    """Spotify handler.

    Settings:
        cachedir
        datadir
        keyfile
        timeout
        stride
    """
    def __init__(self, config):
        name = 'spotify'

        spotify_config = spotify.Config()
        spotify_config.cache_location = \
            os.path.expanduser(config['cachedir'])
        spotify_config.settings_location = \
            os.path.expanduser(config['datadir'])
        spotify_config.load_application_key_file(
            os.path.expanduser(config['keyfile']))

        if not os.path.exists(spotify_config.settings_location):
            os.makedirs(spotify_config.settings_location)

        self._session = spotify.Session(config=spotify_config)

        spotify.AlsaSink(self._session)

        self._pending = Queue.Queue()
        gevent.spawn(self._process_events)
        self._notify()

        self._session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, self._notify)
        self._session.on(spotify.SessionEvent.CONNECTION_ERROR, self.pause)
        self._session.on(spotify.SessionEvent.STREAMING_ERROR, self.pause)
        self._session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, self.pause)
        self._session.on(spotify.SessionEvent.END_OF_TRACK, self.next_track)

        self._timeout = config['timeout']
        self._stride = config['stride']

        self._timeout_context = \
            gevent.Timeout(self._timeout, Exception('Operation timed out'))

        # Playback
        self._playing = False
        self._current_track = None
        self._history = []
        self._track_changed = gevent.event.Event()

        # Queues of searchs
        self._playlist_queue = []
        self._track_queue = []

        # Search
        self._last_search = None

        # Relogin
        self._session.relogin()

    def _process_events(self):
        while True:
            try:
                self._pending.get(False)
            except Queue.Empty:
                gevent.sleep(0.001) # spin
            else:
                try:
                    timeout = self._session.process_events() / 1000.0
                except Exception as e:
                    print(e, file=sys.stderr)
                gevent.spawn_later(timeout, self._notify)

    def _notify(self, *args):
        self._pending.put(1)

    def _guard(self):
        if self.connection_state() not in ('Logged in', 'Offline'):
            raise Exception('You must be logged in to do that')

    @public
    def login(self, username, password):
        """Log in to Spotify."""
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

        result.get(self._timeout)

    @public
    def connection_state(self, *args):
        states = [
            'Logged out',
            'Logged in',
            'Disconnected',
            'Undefined',
            'Offline'
        ]
        return states[self._session.connection.state]

    @public
    def paused(self, *args):
        """Returns whether playback is running."""
        return not self._playing

    @public
    def unpause(self, *args):
        """Resume spotify playback."""
        self._guard()
        if self._current_track:
            self._playing = True
            self._session.player.play()
        return self._playing

    @public
    def pause(self, *args):
        """Pause spotify playback."""
        self._playing = False
        self._session.player.pause()
        return True

    @public
    def current_track(self, *args):
        """Return the currently playing track."""
        return as_dict(self._current_track)

    @public
    def on_track_changed(self, *args):
        """Block until the track changes."""
        self._track_changed.wait()
        return self.current_track()

    @public
    def history(self, *args):
        """Return the track history."""
        return map(as_dict, self._history)

    @public
    def track_queue(self, *args):
        """Return the current track queue."""
        return map(as_dict, self._track_queue)

    @public
    def playlist_queue(self, *args):
        """Return the current playlist queue."""
        return map(as_dict, self._playlist_queue)

    @public
    def lineup(self, *args):
        return self.track_queue() + \
            [as_dict(track) for search in self._playlist_queue
                for track in search.value.track_set]

    def _sync_player(self):
        """Load and play the current track, and prefetch the next."""
        lineup = [search.value for search in self._track_queue] + \
            [track for search in self._playlist_queue
                for track in search.value.track_set]

        try:
            track = lineup[0]
        except IndexError:
            track = None

        if track is not self._current_track:
            self._session.player.load(track.data)
            self._playing = True
            self._session.player.play()
        elif not track:
            self._session.player.unload()

        self._current_track = track
        self._track_changed.set()
        self._track_changed = gevent.event.Event()

        try:
            next_track = lineup[1]
            self._session.player.prefetch(next_track.data)
        except IndexError:
            pass

    def _drop_empty_playlists(self):
        queue = self._playlist_queue
        while queue and not queue[0].value.track_set:
            queue.pop(0)

    @public
    def next_track(self, *args):
        """Load and play the next track."""
        self._guard()
        try:
            self._track_queue.pop(0)
        except IndexError:
            self._drop_empty_playlists()
            try:
                self._playlist_queue[0].value.track_set.pop(0)
            except IndexError:
                pass
            self._drop_empty_playlists()

        if self._current_track:
            self._history.insert(0, self._current_track)
        self._sync_player()
        return self.current_track()

    @public
    def prev_track(self, *args):
        """Load and play the previous track."""
        self._guard()
        if self._history:
            track = self._history.pop(0)
            self._track_queue.insert(0, Single(track))
            self._sync_player()
        return self.current_track()

    @public
    def next_playlist(self, *args):
        """Load an play the next playlist."""
        self._guard()
        try:
            self._playlist_queue.pop(0)
            self._sync_player()
            return as_dict(self._playlist_queue[0])
        except IndexError:
            pass

    @public
    def restart_track(self, *args):
        """Restart the track."""
        self._session.player.seek(0)
        self.unpause()
        return self.current_track()

    @public
    def seek(self, ms):
        """Seek to a position."""
        self._session.player.seek(ms)
        return ms

    def _hold(self, search, queue_type, hold_type):
        def play(l):
            l[0:1] = [search]

        def bump(l):
            l.insert(1, search)

        def queue(l):
            l.append(search)

        hold_types = {
            'play': play,
            'bump': bump,
            'queue': queue
        }

        try:
            hold = hold_types[hold_type]
        except KeyError:
            raise Exception('Unknown hold type')

        queue_types = {
            'track': self._track_queue,
            'playlist': self._playlist_queue
        }

        try:
            queue_list = queue_types[queue_type]
        except KeyError:
            raise Exception('Unknown search type')

        hold(queue_list)
        self._sync_player()

    @public
    def add(self, uri, queue_type, hold_type):
        with self._timeout_context:
            if queue_type == 'track':
                item = Track.load(self._session.get_track(uri))
            elif queue_type == 'playlist':
                item = Playlist.load(self._session.get_playlist(uri))
        self._hold(Single(item), queue_type, hold_type)
        return uri

    @public
    def search(self, query, queue_type, hold_type):
        self._guard()
        with self._timeout_context:
            search = Search.load(self._session,
                query=query, search_type=queue_type, stride=self._stride)
        self._hold(search, queue_type, hold_type)
        self._last_search = search
        return self.last_result()

    @public
    def last_result(self, *args):
        """Return the last search made."""
        return as_dict(self._last_search)

    @public
    def next_result(self, *args):
        """Go to the previous result."""
        self._guard()
        if self._last_search:
            with self._timeout_context:
                self._last_search.next()
            self._sync_player()
        return self.last_result()

    @public
    def prev_result(self, *args):
        """Go to the next result."""
        self._guard()
        if self._last_search:
            self._last_search.prev()
            self._sync_player()
        return self.last_result()
