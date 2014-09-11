import mock
import unittest

import butler
from servants import player

class PlayerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.butler = mock.Mock(spec=butler.Butler)

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
        servant = player.Player(self.butler, {'history_size': 3})

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        servant.history.extend([track3, track2, track1])
        servant.queue.extend([track4, track5, track6])

        servant.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track4, track3, track2],
            current_track=track5,
            queue=[track5, track6])

        servant.seek(314)
        servant.next_track()
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

        servant.seek(314)
        servant.next_track()
        track6.play.assert_called_with(play=False)
        track6.unload.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=False,
            history=[track6, track5, track4],
            current_track=None,
            queue=[])

    def test_prev_track(self):
        servant = player.Player(self.butler, {})

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        servant.history.extend([track3, track2, track1])
        servant.queue.extend([track4, track5, track6])

        servant.seek(314)
        servant.prev_track()
        track3.load.assert_called_with()
        track3.play.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track2, track1],
            current_track=track3,
            queue=[track3, track4, track5, track6])

        servant.next_track()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track3, track2, track1],
            current_track=track4,
            queue=[track4, track5, track6])

        servant.seek(314)
        for _ in range(5):
            servant.prev_track()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[],
            current_track=track1,
            queue=[track1, track2, track3, track4, track5, track6])

    def test_play(self):
        servant = player.Player(self.butler, {})

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        servant.history.extend([track3, track2, track1])
        servant.queue.extend([track4, track5, track6])

        servant.next_track()
        track5.load.assert_called_with()
        track5.play.assert_called_with()
        track6.prefetch.assert_called_with()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track4, track3, track2, track1],
            current_track=track5,
            queue=[track5, track6])

        servant.play(False)
        track5.play.assert_called_with(play=False)
        self.butler.emit.assert_called_with(
            'player.state',
            playing=False,
            history=[track4, track3, track2, track1],
            current_track=track5,
            queue=[track5, track6])

        servant.play(True)
        track5.play.assert_called_with(play=True)
        self.butler.emit.assert_called_with(
            'player.state',
            playing=True,
            history=[track4, track3, track2, track1],
            current_track=track5,
            queue=[track5, track6])

        servant.play(False)
        servant.next_track()
        self.butler.emit.assert_called_with(
            'player.state',
            playing=False,
            history=[track5, track4, track3, track2, track1],
            current_track=track6,
            queue=[track6])
        self.assertFalse(track6.play.called)

    def test_seek(self):
        servant = player.Player(self.butler, {'history_size': 3})

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))
        servant.history.extend([track3, track2, track1])
        servant.queue.extend([track4, track5, track6])

        servant.next_track()
        servant.seek(314)
        track5.seek.assert_called_with(314)
        self.butler.emit.assert_called_with('player.seek', 314)

    @mock.patch.object(player, 'random', autospec=True)
    def test_add(self, random):
        servant = player.Player(self.butler, {'history_size': 3})

        track1, track2, track3, track4, track5, track6 = (
            self._mock_track() for _ in range(6))

        servant.add(0, [track1, track2, track3])
        servant.add(2, [track4, track5, track6])
        self.assertTrue(servant.playing)
        self.assertEqual(servant.current_track, track1)
        self.assertEqual(servant.queue, [track1, track2, track4, track5, track6, track3])

        servant.add(3, [track2, track3, track4], shuffle=True)
        random.shuffle.assert_called_with([track2, track3, track4])
