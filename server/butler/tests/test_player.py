import gevent
import unittest
import mock

from butler.options import Options
from butler.services.player import Metadata, Player, Track, TrackSet

class PlayerTestCase(unittest.TestCase):
    data = {
        'name': 'spam',
        'artist': 'eggs',
        'duration': 1.0,
        'url': 'http://www.foo.org/123',
        'artwork_url': 'http://www.foo.org/123/artwork.jpg',
        'backend': 'music'
    }

    def _mock_tracks(self, count=10, cls=Track):
        for i in range(count):
            data = self.data.copy()
            data['name'] = 'track%i' % (i + 1)
            yield mock.Mock(spec=Track)(Metadata(**data))

    def test_json(self):
        metadata = Metadata(**self.data)
        self.assertEqual(metadata.json(), self.data)

        track = Track(Metadata(**self.data))
        self.assertEqual(track.json(), {
            'type': 'track',
            'metadata': metadata,
        })

        tracks = list(self._mock_tracks())
        track_set = TrackSet(metadata, tracks)
        self.assertEqual(track_set.json(), {
            'type': 'set',
            'metadata': metadata,
            'tracks': tracks
        })

    def test_empty_set(self):
        metadata = Metadata(**self.data)
        with self.assertRaises(ValueError):
            TrackSet(metadata, [])

    def test_options(self):
        service = Player(Options({
            'player': {'history_size': 3}
        }))
        self.assertEqual(service.history.size, 3)

    def test_state(self):
        service = Player(Options())
        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            TrackSet(None, [track4, track5]),
            TrackSet(None, [track6])
        ])

        counter = service.state()['counter']
        marker = []

        def wait_counter():
            service.state(counter=counter)
            marker.append(1)

        gevent.spawn(wait_counter)
        gevent.sleep()
        self.assertFalse(marker)

        service.next_track()
        gevent.sleep()
        self.assertTrue(marker)

    def test_next_track(self):
        service = Player(Options({
            'player': {'history_size': 3}
        }))

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            TrackSet(None, [track4, track5]),
            TrackSet(None, [track6])
        ])

        service.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track4, track3, track2])
        self.assertEqual(service.current_track, track5)

        service.next_track()
        track5.play.assert_called_with(play=False)
        track5.unload.assert_called_with()
        track6.load.assert_called_with()
        track6.play.assert_called_with()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track5, track4, track3])
        self.assertEqual(service.current_track, track6)
        self.assertEqual(len(service.queue), 1)

        service.next_track()
        track6.play.assert_called_with(play=False)
        track6.unload.assert_called_with()
        self.assertFalse(service.playing)
        self.assertEqual(service.current_track, None)
        self.assertEqual(len(service.queue), 0)

    def test_prev_track(self):
        service = Player(Options({
            'player': {'history_size': 3}
        }))

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            TrackSet(None, [track4, track5]),
            TrackSet(None, [track6])
        ])

        service.prev_track()
        track3.load.assert_called_with()
        track3.play.assert_called_with()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track2, track1])
        self.assertEqual(service.current_track, track3)

        service.next_track()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track3, track2, track1])
        self.assertEqual(service.current_track, track4)

        for _ in range(5):
            service.prev_track()
        self.assertTrue(service.playing)
        self.assertEqual(service.current_track, track1)
        self.assertEqual(len(service.queue), 5)

    def test_next_set(self):
        service = Player(Options({
            'player': {'history_size': 3}
        }))

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track2, track1])
        service.queue.extend([
            TrackSet(None, [track3, track4, track5]),
            TrackSet(None, [track6])
        ])

        service.next_track()
        service.next_set()
        self.assertTrue(service.playing)
        self.assertEqual(service.current_track, track6)
        self.assertEqual(service.history, [track4, track3, track2])

    def test_play(self):
        service = Player(Options({
            'player': {'history_size': 3}
        }))

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            TrackSet(None, [track4, track5]),
            TrackSet(None, [track6])
        ])

        service.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.assertTrue(service.playing)

        service.play(play=False)
        track5.play.assert_called_with(play=False)
        self.assertFalse(service.playing)

        service.play(play=False, seek=3.14)
        track5.seek.assert_called_with(3.14)

        service.next_track()
        self.assertEqual(service.current_track, track6)
        self.assertFalse(service.playing)
        self.assertFalse(track6.play.called)

    def test_add(self):
        service = Player(Options({
            'player': {'history_size': 3}
        }))

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)

        service.add(0, TrackSet(None, [track1, track2, track3]))
        self.assertTrue(service.playing)
        self.assertEqual(service.current_track, track1)
