import mock
import unittest

import butler

class EventEmitterTestCase(unittest.TestCase):
    def one(self, *args, **kwds):
        self.calls.append(mock.call('one', *args, **kwds))

    def two(self, *args, **kwds):
        self.calls.append(mock.call('two', *args, **kwds))

    def setUp(self):
        self.emitter = butler.EventEmitter()
        self.calls = []

    def test_on(self):
        self.emitter.on('foo', self.one)
        self.emitter.on('foo', self.two)

        self.emitter.emit('foo', 1, x=3)
        self.emitter.emit('bar', 1, x=3)
        self.emitter.emit('foo', 2, y=4)

        self.assertEqual(self.calls, [
            mock.call('one', 1, x=3),
            mock.call('two', 1, x=3),
            mock.call('one', 2, y=4),
            mock.call('two', 2, y=4),
        ])

    def test_off(self):
        self.emitter.on('foo', self.one);
        self.emitter.on('foo', self.two);
        self.emitter.off('foo', self.two);

        self.emitter.emit('foo');

        self.assertEqual(self.calls, [mock.call('one')])

    def test_off_from_event(self):
        def f():
            self.emitter.off('foo', self.one)
        self.emitter.on('foo', f)
        self.emitter.on('foo', self.one)
        self.emitter.emit('foo');
        self.assertEqual(self.calls, [mock.call('one')])
        self.emitter.emit('foo');
        self.assertEqual(self.calls, [mock.call('one')])

    def test_listeners(self):
        self.emitter.on('foo', self.one)
        self.assertEqual(self.emitter.listeners('foo'), [self.one])
        self.assertEqual(self.emitter.listeners('bar'), [])

class ButlerTestCase(unittest.TestCase):
    class Spam(butler.Servant):
        name = 'spam'

        __init__ = mock.Mock(return_value=None)

        foo = mock.Mock(return_value='bar')
        _hidden = mock.Mock()

    class Eggs(butler.Servant):
        name = 'eggs'

        __init__ = mock.Mock(return_value=None)

    def setUp(self):
        self.butler = butler.Butler({
            'spam': {'foo': 42},
        })
        for servant in (self.Spam, self.Eggs):
            self.butler.hire(servant)

    def test_hire(self):
        self.Spam.__init__.assert_called_with(self.butler, {'foo': 42})
        self.Eggs.__init__.assert_called_with(self.butler, None)

    def test_call(self):
        result = self.butler.call('spam.foo', 1, x=3)
        self.Spam.foo.assert_called_with(1, x=3)
        self.assertEqual(result, 'bar')

        with self.assertRaises(ValueError):
            self.butler.call('spam._hidden')
        self.assertFalse(self.Spam._hidden.called)

class ServantTestCase(unittest.TestCase):
    def one(self):
        pass

    def setUp(self):
        self.butler = mock.Mock(**{
            'call.return_value': 'bar'
        })
        self.servant = butler.Servant(self.butler, {'foo': 42})

    def test_init(self):
        self.assertEqual(self.servant.butler, self.butler)
        self.assertEqual(self.servant.config, {'foo': 42})

    def test_delegate(self):
        self.servant.emit('foo', 1, x=3)
        self.butler.emit.assert_called_with('foo', 1, x=3)

        self.servant.on('foo', self.one)
        self.butler.on.assert_called_with('foo', self.one)

        self.servant.off('foo', self.one)
        self.butler.off.assert_called_with('foo', self.one)

        result = self.servant.call('foo', 1, x=3)
        self.butler.call.assert_called_with('foo', 1, x=3)
        self.assertEqual(result, 'bar')
