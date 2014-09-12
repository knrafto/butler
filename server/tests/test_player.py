import mock
import unittest

import butler
from servants import player

class PlayerTestCase(unittest.TestCase):
    def setUp(self):
        self.butler = mock.Mock(spec=butler.Butler)
        self.player = player.Player(self.butler, {'history_size': 3})

    def _mock_track(self):
        return mock.Mock(spec=player.Track)

    def test_json(self):
        data = {
            'id': 12345,
            'name': 'spam',
            'artist': 'eggs',
            'duration': 1.0,
            'url': 'http://www.foo.org/123',
            'image_url': 'http://www.foo.org/small.jpg',
            'backend': 'music'
        }
        track = player.Track(player.Metadata(**data))
        self.assertEqual(track.json(), data)

    def test_next_track(self):
        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        self.player.history.extend([track3, track2, track1])
        self.player.queue.extend([track4, track5, track6])

        self.player.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track4, track3, track2],
            current_track=track5,
            queue=[track5, track6])

        self.player.seek(314)
        self.player.next_track()
        track5.play.assert_called_with(play=False)
        track5.unload.assert_called_with()
        track6.load.assert_called_with()
        track6.play.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track5, track4, track3],
            current_track=track6,
            queue=[track6])

        self.player.seek(314)
        self.player.next_track()
        track6.play.assert_called_with(play=False)
        track6.unload.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=False,
            history=[track6, track5, track4],
            current_track=None,
            queue=[])

    def test_prev_track(self):
        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        self.player.history.extend([track3, track2, track1])
        self.player.queue.extend([track4, track5, track6])

        self.player.seek(314)
        self.player.prev_track()
        track3.load.assert_called_with()
        track3.play.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track2, track1],
            current_track=track3,
            queue=[track3, track4, track5, track6])

        self.player.next_track()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track3, track2, track1],
            current_track=track4,
            queue=[track4, track5, track6])

        self.player.seek(314)
        for _ in range(5):
            self.player.prev_track()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[],
            current_track=track1,
            queue=[track1, track2, track3, track4, track5, track6])

    def test_play(self):
        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        self.player.history.extend([track3, track2, track1])
        self.player.queue.extend([track4, track5, track6])

        self.player.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track4, track3, track2],
            current_track=track5,
            queue=[track5, track6])

        self.player.play(False)
        track5.play.assert_called_with(play=False)
        self.butler.emit.assert_called_with(
            'player.state',
            playing=False,
            history=[track4, track3, track2],
            current_track=track5,
            queue=[track5, track6])

        self.player.play(True)
        track5.play.assert_called_with(play=True)
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track4, track3, track2],
            current_track=track5,
            queue=[track5, track6])

        self.player.play(False)
        self.player.next_track()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=False,
            history=[track5, track4, track3],
            current_track=track6,
            queue=[track6])
        self.assertFalse(track6.play.called)

    def test_seek(self):
        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        self.player.history.extend([track3, track2, track1])
        self.player.queue.extend([track4, track5, track6])

        self.player.next_track()
        self.player.seek(314)
        track5.seek.assert_called_with(314)
        self.butler.emit.assert_called_with('player.seek', 314)

    @mock.patch.object(player, 'random', autospec=True)
    def test_add(self, random):
        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))

        self.player.add(0, [track1, track2, track3])
        self.player.add(2, [track4, track5, track6])
        self.assertTrue(self.player.playing)
        self.assertEqual(self.player.current_track, track1)
        self.assertEqual(self.player.queue, [track1, track2, track4, track5, track6, track3])
        self.assertFalse(random.shuffle.called)

        self.player.add(3, [track2, track3, track4], shuffle=True)
        random.shuffle.assert_called_with([track2, track3, track4])
