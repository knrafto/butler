import gevent
import mock
import unittest

from butler.options import Options
from butler.services import player

class PlayerTestCase(unittest.TestCase):
    options = Options({'player': {'history_size': 3}})
    metadata = player.Metadata(
        id='12345',
        name='spam',
        artist='eggs',
        duration=1.0,
        url='http://www.foo.org/123',
        images=[
            player.Image(size=64, url='http://www.foo.org/small.jpg'),
            player.Image(size=640, url='http://www.foo.org/large.jpg')],
        backend='music')

    def _mock_tracks(self, count=10):
        for i in range(count):
            data = self.metadata._asdict()
            data['name'] = 'track%i' % (i + 1)
            track = mock.Mock(spec=player.Track)
            track.metadata = player.Metadata(**data)
            yield track

    def test_empty_set(self):
        with self.assertRaises(ValueError):
            player.TrackSet(self.metadata, [])

    def test_options(self):
        service = player.Player(self.options)
        self.assertEqual(service.history.size, 3)

    def test_state(self):
        service = player.Player(Options())
        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            player.TrackSet(None, [track4, track5]),
            player.TrackSet(None, [track6])
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
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            player.TrackSet(None, [track4, track5]),
            player.TrackSet(None, [track6])
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
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            player.TrackSet(None, [track4, track5]),
            player.TrackSet(None, [track6])
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
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track2, track1])
        service.queue.extend([
            player.TrackSet(None, [track3, track4, track5]),
            player.TrackSet(None, [track6])
        ])

        service.next_track()
        service.next_set()
        self.assertTrue(service.playing)
        self.assertEqual(service.current_track, track6)
        self.assertEqual(service.history, [track4, track3, track2])

    def test_play(self):
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)
        service.history.extend([track3, track2, track1])
        service.queue.extend([
            player.TrackSet(None, [track4, track5]),
            player.TrackSet(None, [track6])
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
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = \
            self._mock_tracks(6)

        service.add(0, player.TrackSet(None, [track1, track2, track3]))
        self.assertTrue(service.playing)
        self.assertEqual(service.current_track, track1)
