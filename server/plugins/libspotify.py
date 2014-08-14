from __future__ import print_function

import json
import os
import random
import sys

import gevent
import gevent.event
import Queue
import spotify

class PropertyEncoder(json.JSONEncoder):
    """An encoder that uses a list of properties to serialize an
    object. Takes a dictionary of type: properties.

    >>> class Monty(object):
    ...     def __init__(self, ni):
    ...         self.ni = ni
    ...
    >>> class Spam(object):
    ...     def __init__(self, eggs):
    ...         self.eggs = eggs
    ...     @property
    ...     def knights(self): return Monty('ni')
    ...
    >>> encoder = PropertyEncoder({
    ...     Monty: ('ni',),
    ...     Spam: ('eggs', 'knights')
    ... })
    ...
    >>> encoder.encode(Spam('eggs'))
    '{"knights": {"ni": "ni"}, "eggs": "eggs"}'
    """
    def __init__(self, encoders):
        super(PropertyEncoder, self).__init__()
        self.encoders = encoders

    def default(self, obj):
        try:
            props = self.encoders[type(obj)]
        except KeyError:
            return super(PropertyEncoder, self).default(obj)
        return {
            prop: getattr(obj, prop) for prop in props
        }

encoder = PropertyEncoder({
})

def encode(obj):
    """Encode an object as an iterator."""
    return encoder.iterencode(obj)

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

        self.session = spotify.Session(config)

        spotify.AlsaSink(self.session)

        self._pending = Queue.Queue()
        gevent.spawn(self._process_events)
        self._notify()

        self.session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, self._notify)
        # self._session.on(spotify.SessionEvent.CONNECTION_ERROR, self.pause)
        # self._session.on(spotify.SessionEvent.STREAMING_ERROR, self.pause)
        # self._session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, self.pause)
        # self._session.on(spotify.SessionEvent.END_OF_TRACK, self.next_track)

        self.timeout = timeout

        # Playback
        self.playing = False
        self.current_track = None
        self.history = []
        self.queue = []

        self.player_state_changed = gevent.event.Event()

        # Relogin
        self.session.relogin()

    def _process_events(self):
        while True:
            try:
                self._pending.get(False)
            except Queue.Empty:
                gevent.sleep(0.001) # spin
            else:
                try:
                    timeout = self.session.process_events() / 1000.0
                except Exception as e:
                    print(e, file=sys.stderr)
                gevent.spawn_later(timeout, self._notify)

    def _notify(self, *args):
        self._pending.put(1)

    # def _guard(self):
    #     if self.connection_state() not in ('Logged in', 'Offline'):
    #         raise Exception('You must be logged in to do that')

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

    # @public
    # def connection_state(self, *args):
    #     states = [
    #         'Logged out',
    #         'Logged in',
    #         'Disconnected',
    #         'Undefined',
    #         'Offline'
    #     ]
    #     return states[self._session.connection.state]

    # def _lineup(self, *args):
    #     return [search.value for search in self._track_queue] + \
    #         [track for search in self._playlist_queue
    #             for track in search.value.track_set]

    # @public
    # def player_state(self, *args):
    #     """Return the current player state."""
    #     return {
    #         'paused':         not self._playing,
    #         'current_track':  as_dict(self._current_track),
    #         'history':        map(as_dict, self._history),
    #         'track_queue':    map(as_dict, self._track_queue),
    #         'playlist_queue': map(as_dict, self._playlist_queue),
    #         'lineup':         map(as_dict, self._lineup())
    #     }

    # @public
    # def on_player_state_changed(self, *args):
    #     """Block until the track changes."""
    #     self._player_state_changed.wait()
    #     return self.player_state()

    # def _sync_player(self):
    #     """Load and play the current track, and prefetch the next."""
    #     lineup = self._lineup()

    #     try:
    #         track = lineup[0]
    #     except IndexError:
    #         track = None

    #     if track and track is not self._current_track:
    #         self._session.player.load(track.data)
    #         self._playing = True
    #         self._session.player.play()
    #     elif not track:
    #         self._playing = False
    #         self._session.player.unload()

    #     self._current_track = track
    #     self._player_state_changed.set()
    #     self._player_state_changed = gevent.event.Event()

    #     try:
    #         next_track = lineup[1]
    #         self._session.player.prefetch(next_track.data)
    #     except IndexError:
    #         pass

    # def _drop_empty_playlists(self):
    #     queue = self._playlist_queue
    #     while queue and not queue[0].value.track_set:
    #         queue.pop(0)

    # @public
    # def next_track(self, *args):
    #     """Load and play the next track."""
    #     self._guard()
    #     try:
    #         self._track_queue.pop(0)
    #     except IndexError:
    #         self._drop_empty_playlists()
    #         try:
    #             self._playlist_queue[0].value.track_set.pop(0)
    #         except IndexError:
    #             pass
    #         self._drop_empty_playlists()

    #     if self._current_track:
    #         self._history.insert(0, self._current_track)
    #     self._sync_player()
    #     return self.player_state()

    # @public
    # def prev_track(self, *args):
    #     """Load and play the previous track."""
    #     self._guard()
    #     if self._history:
    #         track = self._history.pop(0)
    #         self._track_queue.insert(0, Single(track))
    #         self._sync_player()
    #     return self.player_state()

    # @public
    # def next_playlist(self, *args):
    #     """Load an play the next playlist."""
    #     self._guard()
    #     try:
    #         self._playlist_queue.pop(0)
    #         self._sync_player()
    #         return as_dict(self._playlist_queue[0])
    #     except IndexError:
    #         pass

    # @public
    # def unpause(self, *args):
    #     """Resume spotify playback."""
    #     if self._current_track:
    #         self._playing = True
    #         self._session.player.play()
    #     return self.player_state()

    # @public
    # def pause(self, *args):
    #     """Pause spotify playback."""
    #     self._playing = False
    #     self._session.player.pause()
    #     return self.player_state()

    # @public
    # def seek(self, ms):
    #     """Seek to a position."""
    #     self._session.player.seek(ms)
    #     return ms

    # def _hold(self, search, queue_type, hold_type):
    #     def play(l):
    #         l[0:1] = [search]

    #     def bump(l):
    #         l.insert(1, search)

    #     def queue(l):
    #         l.append(search)

    #     hold_types = {
    #         'play': play,
    #         'bump': bump,
    #         'queue': queue
    #     }

    #     try:
    #         hold = hold_types[hold_type]
    #     except KeyError:
    #         raise Exception('Unknown hold type')

    #     queue_types = {
    #         'track': self._track_queue,
    #         'playlist': self._playlist_queue
    #     }

    #     try:
    #         queue_list = queue_types[queue_type]
    #     except KeyError:
    #         raise Exception('Unknown search type')

    #     hold(queue_list)
    #     self._sync_player()

    # @public
    # def add_uri(self, uri, queue_type, hold_type):
    #     with self._timeout_context:
    #         if queue_type == 'track':
    #             item = Track.load(self._session.get_track(uri))
    #         elif queue_type == 'playlist':
    #             item = Playlist.load(self._session.get_playlist(uri))
    #     self._hold(Single(item), queue_type, hold_type)
    #     return uri

    # @public
    # def add_query(self, query, queue_type, hold_type):
    #     self._guard()
    #     with self._timeout_context:
    #         search = Search.load(self._session, query,
    #             queue_type, self._stride)
    #     self._hold(search, queue_type, hold_type)
    #     self._last_search = search
    #     return self.last_result()

    # @public
    # def last_result(self, *args):
    #     """Return the last search made."""
    #     return as_dict(self._last_search)

    # @public
    # def next_result(self, *args):
    #     """Go to the previous result."""
    #     self._guard()
    #     if self._last_search:
    #         with self._timeout_context:
    #             self._last_search.next()
    #         self._sync_player()
    #     return self.last_result()

    # @public
    # def prev_result(self, *args):
    #     """Go to the next result."""
    #     self._guard()
    #     if self._last_search:
    #         self._last_search.prev()
    #         self._sync_player()
    #     return self.last_result()

    # @public
    # def search(self, query, search_type, offset=0, stride=None):
    #     self._guard()
    #     results = Search.search(self._session, query,
    #         search_type, offset, stride)
    #     return map(as_dict, results)
