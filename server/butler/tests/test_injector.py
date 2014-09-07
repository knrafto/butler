import unittest

from butler import injector

class InjectorTestCase(unittest.TestCase):
    def test_get(self):
        provider = injector.Injector()

        @provider.register('spam', [])
        def spam():
            return 'spam'

        @provider.register('eggs', ['spam'])
        def eggs(spam):
            return 'eggs (with %s)' % spam

        @provider.register('both', ['spam', 'eggs'])
        def both(spam, eggs):
            return '%s and %s' % (spam, eggs)

        self.assertEqual(provider.get('both'), 'spam and eggs (with spam)')
        self.assertEqual(provider.get('spam'), 'spam')
        self.assertEqual(provider.get('eggs'), 'eggs (with spam)')

    def test_cyclic(self):
        provider = injector.Injector()

        @provider.register('spam', ['eggs'])
        def spam(eggs):
            return 'spam'

        @provider.register('eggs', ['spam'])
        def eggs(spam):
            return 'eggs'

        @provider.register('ni', ['ni'])
        def ni(ni):
            return ni

        with self.assertRaises(injector.InjectionError):
            provider.get('spam')
        with self.assertRaises(injector.InjectionError):
            provider.get('ni')

    def test_missing(self):
        provider = injector.Injector()

        @provider.register('spam', ['eggs'])
        def spam(eggs):
            return 'spam'

        with self.assertRaises(injector.InjectionError):
            provider.get('spam')
