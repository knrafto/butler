import unittest

import gevent

from butler.utils import Counter, Queue

class CounterTestCase(unittest.TestCase):
    def test_initial(self):
        counter = Counter()
        self.assertEqual(counter.value, 0)

        counter = Counter(5)
        self.assertEqual(counter.value, 5)

    def test_set(self):
        counter = Counter()
        counter.set(5)
        self.assertEqual(counter.value, 5)
        counter.set()
        self.assertEqual(counter.value, 6)

    def test_wait_none(self):
        counter = Counter(5)
        self.assertEqual(counter.wait(), 5)

    def test_wait_lt(self):
        counter = Counter(5)
        self.assertEqual(counter.wait(4), 5)

    def test_wait_ge(self):
        marker = []
        counter = Counter()

        def set_counter():
            for i in range(5):
                if i == 4:
                    marker.append(1)
                counter.set(i)
                gevent.sleep(0.001)

        gevent.spawn(set_counter)
        counter.wait(3)
        self.assertTrue(marker)

    def test_wait_timeout(self):
        counter = Counter()

        def set_counter():
            for i in range(5):
                counter.set(i)
                gevent.sleep(0.001)

        gevent.spawn(set_counter)
        with self.assertRaises(gevent.Timeout):
            counter.wait(3, timeout=0.002)

class QueueTestCase(unittest.TestCase):
    def test_size(self):
        q = Queue(size=3)
        for i in range(5):
            q.append(i)
        self.assertEqual(q, [0, 1, 2])
        q.pop(1)
        self.assertEqual(q, [0, 2])
        q.extend([3, 4, 5])
        self.assertEqual(q, [0, 2, 3])
        q.insert(1, 1)
        self.assertEqual(q, [0, 1, 2])

    def test_default(self):
        q = Queue()
        for i in range(5):
            q.append(i)
        self.assertEqual(q, [0, 1, 2, 3, 4])
