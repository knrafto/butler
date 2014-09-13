import collections
import random

import gevent

import butler

Metadata = collections.namedtuple(
    'Metadata',
    'id name artist duration url image_url backend')

class Track(object):
    def __init__(self, metadata):
        self.metadata = metadata

    def load(self):
        raise NotImplementedError

    def unload(self):
        raise NotImplementedError

    def prefetch(self):
        raise NotImplementedError

    def play(self, play=True):
        raise NotImplementedError

    def seek(self, ms):
        raise NotImplementedError

    def json(self):
        return self.metadata._asdict()

    def __eq__(self, other):
        return isinstance(other, Track) and self.metadata == other.metadata

class Player(butler.Servant):
    """A music player service."""
    name = 'player'

    def __init__(self, butler, config):
        super(Player, self).__init__(butler, config)
        self.history_size = config.get('history_size', None)
        self.playing = False
        self.current_track = None
        self.history = []
        self.queue = []

    def state(self):
        return dict(
            playing=self.playing,
            current_track=self.current_track,
            history=self.history,
            queue=self.queue)

    def _emit_state(self):
        self.emit('player.state', **self.state())

    def _sync_player(self):
        """Load and play the current track, and prefetch the next."""

        try:
            track = self.queue[0]
        except IndexError:
            track = None
        if track != self.current_track:
            if self.current_track:
                self.current_track.play(play=False)
                self.current_track.unload()
            if track:
                track.load()
                if self.playing or not self.current_track:
                    track.play()
                    self.playing = True
            else:
                self.playing = False
            self.current_track = track
        try:
            next_track = self.queue[1]
        except IndexError:
            pass
        else:
            next_track.prefetch()
        self._emit_state()

    def next_track(self):
        """Load and play the next track."""
        try:
            prev_track = self.queue.pop(0)
        except IndexError:
            pass
        else:
            self.history.insert(0, prev_track)
            if self.history_size is not None:
                while len(self.history) > self.history_size:
                    self.history.pop()
            self._sync_player()

    def prev_track(self,):
        """Load and play the previous track."""
        try:
            prev_track = self.history.pop(0)
        except IndexError:
            pass
        else:
            self.queue.insert(0, prev_track)
            self._sync_player()

    def play(self, play=True):
        """Resume playback."""
        if self.current_track:
            self.playing = play
            self.current_track.play(play=play)
            self._emit_state()

    def seek(self, ms):
        """Seek to a position, in milliseconds."""
        if self.current_track:
            self.current_track.seek(ms)
            self.emit('player.seek', ms)

    def add(self, index, tracks, shuffle=False):
        """Add tracks at an index in the queue."""
        if shuffle:
            tracks = tracks[:]
            random.shuffle(tracks)
        self.queue[index:index] = tracks
        self._sync_player()
