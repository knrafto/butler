import collections
import random

from butler.options import Options
from butler.routing import endpoint
from butler.service import singleton
from butler.utils import Counter, Queue

class Metadata(collections.namedtuple(
        'Metadata',
        'id name artist duration url image_url backend')):
    def json(self):
        return self._asdict()

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

    def seek(self, seconds):
        raise NotImplementedError

    def json(self):
        return self.metadata.json()

class TrackSet(object):
    def __init__(self, metadata, tracks, shuffle=False):
        if not tracks:
            raise ValueError('empty track set')
        self.metadata = metadata
        self.tracks = list(tracks)
        self.shuffle = shuffle
        if shuffle:
            random.shuffle(self.tracks)

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.tracks.pop(0)
        except IndexError:
            raise StopIteration

    def json(self):
        d = self.metadata.json()
        d['tracks'] = self.tracks
        return d

    @classmethod
    def singleton(cls, track):
        return cls(track.metadata, [track])

@singleton
class Player(object):
    """A music player service."""
    name = 'player'
    depends = ['options']

    def __init__(self, options):
        options = options.options(self.name)
        history_size = options.int('history_size', None)
        self.playing = False
        self.current_track = None
        self.history = Queue(size=history_size)
        self.queue = []
        self.state_counter = Counter()

    def _sync_player(self):
        """Load and play the current track, and prefetch the next."""
        lineup = [track for track_set in self.queue
            for track in track_set.tracks]
        try:
            track = lineup[0]
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
            next_track = lineup[1]
        except IndexError:
            pass
        else:
            next_track.prefetch()
        self.state_counter.set()

    @endpoint('/state')
    def state(self, **kwds):
        """Return the current player state."""
        counter = Options(kwds).int('counter', None)
        counter = self.state_counter.wait(counter)
        d = {prop: getattr(self, prop)
            for prop in 'playing current_track queue history'.split()}
        d['counter'] = counter
        return d

    @endpoint('/next_track', methods=['POST'])
    def next_track(self, **kwds):
        """Load and play the next track."""
        try:
            track_set = self.queue[0]
        except IndexError:
            pass
        else:
            last_track = track_set.next()
            if not track_set.tracks:
                self.queue.pop(0)
            self.history.insert(0, last_track)
        self._sync_player()

    @endpoint('/prev_track', methods=['POST'])
    def prev_track(self, **kwds):
        """Load and play the previous track."""
        try:
            prev_track = self.history.pop(0)
        except IndexError:
            pass
        else:
            self.queue.insert(0, TrackSet.singleton(prev_track))
        self._sync_player()

    @endpoint('/next_set', methods=['POST'])
    def next_set(self, **kwds):
        """Load and play the next track set."""
        if self.current_track:
            self.history.insert(0, self.current_track)
        try:
            self.queue.pop(0)
        except IndexError:
            pass
        self._sync_player()

    @endpoint('/play', methods=['POST'])
    def play(self, **kwds):
        """Resume spotify playback.

        Parameters:
            pause: If true, pause playback
            seek: Seek position, in milliseconds
        """
        options = Options(kwds)
        seek = options.float('seek', None)
        play = not options.bool('pause')
        if self.current_track:
            if seek is not None:
                self.current_track.seek(seek)
            self.playing = play
            self.current_track.play(play=play)
        self.state_counter.set()

    def add(self, index, track_set):
        """Add a track at an index in the queue."""
        self.queue.insert(index, track_set)
        self._sync_player()
