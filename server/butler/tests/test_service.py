import unittest

from butler import service

class ServiceTestCase(unittest.TestCase):
    def test_create(self):
        foo = service.Service('foo', ('bar', 'baz'),
            lambda bar, baz: "%s and %s" % (bar, baz))
        created = {
            'bar': 'spam',
            'baz': 'eggs',
            'quux': 'baked beans'
        }
        self.assertEqual(foo.create(created), "spam and eggs")

    def test_str_repr(self):
        foo = service.Service('foo', ('bar', 'baz'),
            lambda bar, baz: "%s and %s" % (bar, baz))
        self.assertEqual(repr(foo), "<Service 'foo'>")
        self.assertEqual(repr(foo), "<Service 'foo'>")

    def test_topsort(self):
        G = {
            1: [],
            2: [1],
            3: [6, 2],
            4: [3, 2],
            5: [4]
        }
        self.assertEqual(service.topsort(G), [5, 4, 3, 2, 1])
        G = {
            1: [2],
            2: [1]
        }
        with self.assertRaises(service.DependencyError):
            service.topsort(G)

    def test_start(self):
        services = [
            service.Service('foo', ('bar', 'baz'),
                lambda bar, baz: "%s and %s" % (bar, baz)),
            service.Service('bar', (), lambda: 'spam'),
            service.Service('baz', (), lambda: 'eggs'),
            service.Service('quux', ['foo'], lambda foo: foo)
        ]
        self.assertEqual(service.start(services), {
            'foo': 'spam and eggs',
            'bar': 'spam',
            'baz': 'eggs',
            'quux': 'spam and eggs'
        })
        with self.assertRaises(service.DependencyError):
            service.start(services[1:])

    def test_singleton(self):
        @service.singleton
        class Foo(object):
            name = 'foo'
            depends = ('bar', 'baz')

            def __init__(self, bar, baz):
                self.foo = "%s and %s" % (bar, baz)

        services = [
            Foo,
            service.static('bar', 'spam'),
            service.static('baz', 'eggs')
        ]
        started = service.start(services)
        self.assertEqual(started['foo'].foo, 'spam and eggs')

    def test_static(self):
        services = [
            service.static('foo', 'spam and eggs'),
            service.Service('quux', ['foo'], lambda foo: foo)
        ]
        self.assertEqual(service.start(services), {
            'foo': 'spam and eggs',
            'quux': 'spam and eggs'
        })
