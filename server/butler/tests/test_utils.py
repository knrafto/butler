import unittest

import gevent

from butler import utils

class CounterTestCase(unittest.TestCase):
    def test_initial(self):
        counter = utils.Counter()
        self.assertEqual(counter.value, 0)

        counter = utils.Counter(5)
        self.assertEqual(counter.value, 5)

    def test_set(self):
        counter = utils.Counter()
        counter.set(5)
        self.assertEqual(counter.value, 5)
        counter.set()
        self.assertEqual(counter.value, 6)

    def test_wait_none(self):
        counter = utils.Counter(5)
        self.assertEqual(counter.wait(), 5)

    def test_wait_lt(self):
        counter = utils.Counter(5)
        self.assertEqual(counter.wait(4), 5)

    def test_wait_ge(self):
        marker = []
        counter = utils.Counter()

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
        counter = utils.Counter()

        def set_counter():
            for i in range(5):
                counter.set(i)
                gevent.sleep(0.001)

        gevent.spawn(set_counter)
        with self.assertRaises(gevent.Timeout):
            counter.wait(3, timeout=0.002)
