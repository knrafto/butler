import unittest

import butler

class ButlerTestCase(unittest.TestCase):
    class Spam(butler.Servant):
        name = 'spam'

        def sausage(self, *args, **kwds):
            return args, kwds

        def _hidden(self):
            raise TypeError

    class Eggs(butler.Servant):
        name = 'eggs'

    @classmethod
    def setUpClass(cls):
        cls.butler = butler.Butler({
            'spam': {'foo': 42},
        })
        for servant in (cls.Spam, cls.Eggs):
            cls.butler.hire(servant)

    def test_hire(self):
        self.assertEqual(self.butler.get('spam').config, {'foo': 42})
        self.assertEqual(self.butler.get('eggs').config, None)

    def test_emit(self):
        called = []
        def f(spam, knights=None):
            called.append('f')
            self.assertEqual(spam, 'spam')
            self.assertEqual(knights, 'ni')

        def g(*args, **kwds):
            called.append('g')

        self.butler.on('spam.hi', f)
        self.butler.on('spam.hi', g)
        self.butler.emit('spam.hi', 'spam', knights='ni')
        self.assertEqual(called, ['f', 'g'])

        called = []
        self.butler.off('spam.hi', f)
        self.butler.emit('spam.hi', 'spam', knights='ni')
        self.assertEqual(called, ['g'])

        called = []
        self.butler.on('spam.hi', f)
        self.butler.get('eggs').emit('spam.hi', 'spam', knights='ni')
        self.assertEqual(called, ['g', 'f'])

    def test_call(self):
        args, kwds = self.butler.call('spam.sausage', 'bacon', muffin='english')
        self.assertEqual(list(args), ['bacon'])
        self.assertEqual(kwds, {'muffin': 'english'})

        args, kwds = self.butler.get('eggs').call('spam.sausage', 'bacon', muffin='english')
        self.assertEqual(list(args), ['bacon'])
        self.assertEqual(kwds, {'muffin': 'english'})

        with self.assertRaises(ValueError):
            self.butler.call('spam._hidden')
