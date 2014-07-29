from os import path
from twisted.internet import defer, reactor
import spotify

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

        self._pending = None
        self._process_events()

        def notify(session):
            reactor.callFromThread(self._process_events)

        self._session.on(spotify.SessionEvent.NOTIFY_MAIN_THREAD, notify)

    def _process_events(self):
        if self._pending and self._pending.active():
            self._pending.cancel()
        timeout = self._session.process_events() / 1000.0
        self._pending = reactor.callLater(timeout, self._process_events)

    def login(self, username=None, password=None):
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
