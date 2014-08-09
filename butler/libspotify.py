from __future__ import print_function

import os
import random
import sys

import gevent
import gevent.event
import Queue
import spotify
from tinyrpc.dispatch import public

# class Search(object):
#     """A list of items from a Spotify search."""
#     def __init__(self, session, query, search_type, stride):
#         self._items = []
#         self._index = 0

#         self._result = gevent.event.AsyncResult()
#         session.search(query, self._loaded, **kwds)
#         gevent.spawn(self._append_result)

#     def value(self, timeout=None):
#         try:
#             return self._items[self._index]
#         except IndexError:
#             return None

#     def next(self):
#         self._index += 1
#         if self._index >= len(self._items):
#             results = self._more()
#             self._append_results(results)
#         if self._index >= len(self._items):
#             self._index = len(self._items) - 1

#     def prev(self):
#         if self._index > 0:
#             self._index -= 1

#     def _loaded(self, deferred, search):
#         try:
#             results = list(self._selector(search))
#             print results
#             if not results:
#                 raise xmlrpc.Fault(1, 'no results')
#         except Exception as e:
#             deferred.errback(e)
#         else:
#             deferredList = handler.wait_all(results)
#             deferredList.chainDeferred(deferred)
#         return False

#     def _append_result(self):
#         results = self._result.get()
#         self._result = None
#         if not results:
#             raise ValueError('No results')
#         self._items.extend(results)

#     def _more(self):
#         """Asynchronously load more results."""
#         self._result = gevent.event.AsyncResult()
#         self._last_search.more(self._loaded)
#         gevent.spawn(self._append_result)
#         return result.get()

class Single(object):
    def __init__(self, item):
        self._item = item

    def value(self):
        return self._item

class Track(object):
    def __init__(self, track):
        self._track = track
        self._result = gevent.event.AsyncResult()
        self._load()

        session = self._track._session

        def check_loaded(session):
            if self._loaded():
                return False

        if not _loaded():
            session.on(spotify.SessionEvent.METADATA_UPDATED, check_loaded)

    @property
    def data(self):
        return self._track

    def get(self, timeout=None):
        return self._result.get(timeout)

    def encode(self):
        track = self.get()
        return {
            'type': 'Track',
            'name': track.name,
            'uri': track.link.uri
        }

    def _loaded(self):
        if not self._track.is_loaded:
            return False

        try:
            spotify.Error.maybe_raise(self._track.error)
        except spotify.LibError as e:
            self._result.set_exception(e)
        else:
            self._result.set(self._track)
        return True

class Playlist(object):
    def __init__(self, playlist, shuffle=False):
        if isinstance(playlist, spotify.SearchPlaylist):
            playlist = playlist.playlist

        self._playlist = playlist
        self._shuffle = shuffle
        self._result = gevent.event.AsyncResult()

        def check_loaded(playlist):
            if self._loaded():
                return False

        if not self._loaded():
            playlist.on(spotify.PlaylistEvent.PLAYLIST_STATE_CHANGED, check_loaded)
        # TODO: tracks added, removed

    def get(self, timeout=None):
        return self._result.get(timeout)

    def track_set(self):
        self.get()
        return self._track_set

    def next(self):
        self.get()
        try:
            self._track_set.pop(0)
        except IndexError:
            pass

    def encode(self):
        playlist = self.get()
        return {
            'type': 'Playlist',
            'name': playlist.name,
            'uri': playlist.link.uri
        }

    def _loaded(self):
        if not self._playlist.is_loaded:
            return False

        self._track_set = [Track(track) for track in self._playlist.tracks]
        if self._shuffle:
            random.shuffle(self._track_set)

        self._result.set(self._playlist)
        return True

class Spotify(object):
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

        spotify_config = spotify.Config()
        if 'cache_dir' in config:
            spotify_config.cache_location = \
                os.path.expanduser(config['cache_dir'])
        if 'data_dir' in config:
            spotify_config.settings_location = \
                os.path.expanduser(config['data_dir'])
        if 'key_file' in config:
            spotify_config.load_application_key_file(
                os.path.expanduser(config['key_file']))

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
        # self._session.on(spotify.SessionEvent.END_OF_TRACK, self.next_track)

        self._timeout = int(config.get('timeout', 30))
        self._results = int(config.get('results', 5))

        # Playback
        self._playing = False
        self._current_track = None
        self._history = []

        # Queues of searchs
        self._playlist_queue = []
        self._track_queue = []

        # Search
        self._last_search = None

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

    @public
    def login(self, username=None, password=None):
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

        if username is None:
            self._session.relogin()
        elif password:
            self._session.login(username, password, remember_me=True);
        else:
            raise ValueError('Password required')

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

    @public
    def current_track(self):
        """Return the currently playing track."""
        with gevent.Timeout(self._timeout):
            if self._current_track:
                return self._current_track.encode()

    @public
    def history(self):
        """Return the track history."""
        with gevent.Timeout(self._timeout):
            return [track.encode() for track in self._history]

    @handler.method
    def track_queue(self):
        """Return the current track queue."""
        with gevent.Timeout(self._timeout):
            return [search.value().encode() for search in self._track_queue]

    @handler.method
    def playlist_queue(self):
        """Return the current playlist queue."""
        with gevent.Timeout(self._timeout):
            return [search.value().encode() for search in self._playlist_queue]

    @handler.method
    def lineup(self):
        """Return the next tracks to play."""
        with gevent.Timeout(self._timeout):
            return track_queue() + playlist_queue()

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

    def _drop_empty_playlists(self):
        queue = self._playlist_queue
        while queue and not queue[0].track_set():
            queue.pop(0)

    @handler.method
    def next_track(self, *args):
        """Load and play the next track."""
        with gevent.Timeout(self._timeout):
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
            return self._current_track.encode()

    @handler.method
    def prev_track(self, *args):
        """Load and play the previous track."""
        with gevent.Timeout(self._timeout):
            if self._history:
                track = self._history.pop(0)
                self._track_queue.insert(0, Single(track))
                self._sync_player()
            return self._current_track.encode()

    @handler.method
    def next_playlist(self, *args):
        """Load an play the next playlist."""
        with gevent.Timeout(self._timeout):
            try:
                self._playlist_queue.pop(0)
                self._sync_player()
                return self._playlist_queue[0].encode()
            except IndexError:
                pass

    @handler.method
    def restart_track(self, *args):
        """Restart the track."""
        with gevent.Timeout(self._timeout):
            self._session.player.seek(0)
            self.unpause()
            return self._current_track.encode()

    @handler.method
    def last_result(self, *args):
        """Return the last search made."""
        if self._last_search:
            return self._last_search.value().encode()

    @handler.method
    @defer.inlineCallbacks
    def next_result(self, *args):
        """Go to the previous result."""
        if self._last_search:
            self._last_search.next()
            self._sync_player()
        return self.last_result()

    @handler.method
    @defer.inlineCallbacks
    def prev_result(self, *args):
        """Go to the next result."""
        if self._last_search:
            self._last_search.prev()
            self._sync_player()
        return self.last_result()

    def _search(self, query, search_type, hold):
        with gevent.event.Timeout(self._timeout):
            search = Search(self._session, query, search_type, self._results)
            self._last_search = search
            hold(search)
            self._sync_player
            return self.last_result()

    @public
    def play_track(self, query):
        """Play a track now."""
        def hold(search):
            self._track_queue[0:1] = [search]

        return self._search(query, 'track', hold)

    @public
    def bump_track(self, query):
        """Play a track next."""
        def hold(search):
            self._track_queue.insert(1, search)

        return self._search(query, 'track', hold)

    @public
    def queue_track(self, query):
        """Place a track at the end of the queue."""
        def hold(search):
            self._track_queue.append(search)

        return self._search(query, 'track', hold)

    @public
    def play_playlist(self, query):
        """Play a playlist now."""
        def hold(search):
            self._playlist_queue[0:1] = [search]

        return self._search(query, 'playlist', hold)

    @public
    def bump_playlist(self, query):
        """Play a playlist next."""
        def hold(search):
            self._playlist_queue.insert(1, search)

        return self._search(query, 'playlist', hold)

    @public
    def queue_playlist(self, query):
        """Place a playlist at the end of the queue."""
        def hold(search):
            self._playlist_queue.append(search)

        return self._search(query, 'playlist', hold)
