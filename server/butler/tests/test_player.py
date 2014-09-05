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
        image_url='http://www.foo.org/small.jpg',
        backend='music')

    def _mock_track(self):
        return mock.Mock(spec=player.Track)

    def test_options(self):
        service = player.Player(self.options)
        self.assertEqual(service.history.size, 3)

    def test_state(self):
        service = player.Player(Options())
        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        service.history.extend([track3, track2, track1])
        service.queue.extend([track4, track5, track6])

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

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        service.history.extend([track3, track2, track1])
        service.queue.extend([track4, track5, track6])

        service.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track4, track3, track2])
        self.assertEqual(service.current_track, track5)
        self.assertEqual(service.queue, [track5, track6])

        service.next_track()
        track5.play.assert_called_with(play=False)
        track5.unload.assert_called_with()
        track6.load.assert_called_with()
        track6.play.assert_called_with()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track5, track4, track3])
        self.assertEqual(service.current_track, track6)
        self.assertEqual(service.queue, [track6])
        self.assertEqual(len(service.queue), 1)

        service.next_track()
        track6.play.assert_called_with(play=False)
        track6.unload.assert_called_with()
        self.assertFalse(service.playing)
        self.assertEqual(service.history, [track6, track5, track4])
        self.assertEqual(service.current_track, None)
        self.assertEqual(service.queue, [])

    def test_prev_track(self):
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        service.history.extend([track3, track2, track1])
        service.queue.extend([track4, track5, track6])

        service.prev_track()
        track3.load.assert_called_with()
        track3.play.assert_called_with()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track2, track1])
        self.assertEqual(service.current_track, track3)
        self.assertEqual(service.queue, [track3, track4, track5, track6])

        service.next_track()
        self.assertTrue(service.playing)
        self.assertEqual(service.history, [track3, track2, track1])
        self.assertEqual(service.current_track, track4)

        for _ in range(5):
            service.prev_track()
        self.assertTrue(service.playing)
        self.assertEqual(service.current_track, track1)
        self.assertEqual(service.queue, [track1, track2, track3, track4, track5, track6])

    def test_play(self):
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        service.history.extend([track3, track2, track1])
        service.queue.extend([track4, track5, track6])

        service.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.assertTrue(service.playing)

        service.play(pause=True)
        track5.play.assert_called_with(play=False)
        self.assertFalse(service.playing)

        service.play(pause=False)
        track5.play.assert_called_with(play=True)
        self.assertTrue(service.playing)

        service.play(pause=True)
        service.next_track()
        self.assertEqual(service.current_track, track6)
        self.assertFalse(service.playing)
        self.assertFalse(track6.play.called)

    def test_seek(self):
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        service.history.extend([track3, track2, track1])
        service.queue.extend([track4, track5, track6])

        service.next_track()
        service.seek(seek=3.14)
        track5.seek.assert_called_with(3.14)

    @mock.patch.object(player, 'random', autospec=True)
    def test_add(self, random):
        service = player.Player(self.options)

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))

        service.add(0, [track1, track2, track3])
        service.add(2, [track4, track5, track6])
        self.assertTrue(service.playing)
        self.assertEqual(service.current_track, track1)
        self.assertEqual(service.queue, [track1, track2, track4, track5, track6, track3])

        service.add(3, [track2, track3, track4], shuffle=True)
        random.shuffle.assert_called_with([track2, track3, track4])
