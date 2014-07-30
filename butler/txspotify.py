from os import path
import sys

import spotify
from twisted.internet import defer, reactor

SpotifyError = spotify.LibError

class Session:
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

        def notify(session):
            reactor.callFromThread(self._process_events)

        self._session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, notify)

    def _process_events(self):
        """Process spotify events and schedule the next timeout."""
        if self._pending and self._pending.active():
            self._pending.cancel()
        timeout = self._session.process_events() / 1000.0
        self._pending = reactor.callLater(timeout, self._process_events)

    def login(self, username=None, password=None):
        """Asynchronously log in to Spotify."""
        d = defer.Deferred()

        def logged_in(session, error_type):
            if error_type == spotify.ErrorType.OK:
                d.callback(None)
            else:
                d.errback(spotify.LibError(error_type))
            return False

        self._session.on(spotify.SessionEvent.LOGGED_IN, logged_in)

        if username is None:
            self._session.relogin()
        else:
            self._session.login(username, password, remember_me=True);
        return d

    def load(self, track):
        """Load a track for playback."""
        self._session.player.load(track)

    def play(self, play=True):
        """Play or pause playback."""
        self._session.player.play(play)

    def search(self, query):
        """Asynchronously load a search."""
        d = defer.Deferred()

        def loaded(search):
            if search.error == spotify.ErrorType.OK:
                d.callback(search)
            else:
                d.errback(spotify.LibError(search.error))
            return False

        self._session.search(query, loaded)
        return d
