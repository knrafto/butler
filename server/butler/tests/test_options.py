import os
import unittest

from butler.options import Options

class OptionsTestCase(unittest.TestCase):
    def test_init(self):
        value = {
            'foo': 42,
            'bar': 'blub'
        }
        options = Options(value)
        self.assertEqual(len(options), len(value))
        for key in value:
            self.assertEqual(options[key], value[key])

        for value in (None, 1, 'spam'):
            options = Options(value)
            self.assertEqual(len(options), 0)

    def test_get(self):
        options = Options({
            'foo': '42',
            'bar': 'blub'
        })
        self.assertEqual(options.get('foo', None), '42')
        self.assertEqual(options.get('foo', None, type=int), 42)
        self.assertEqual(options.get('foo', None, type=dict), None)
        self.assertEqual(options.get('bar', 'oops', type=int), 'oops')
        self.assertEqual(options.get('baz', None), None)

    def test_options(self):
        options = Options({
            'foo': {
                'spam': 'eggs',
                'knights': 'ni'
            },
            'bar': 'blub'
        })
        suboptions = Options({
            'spam': 'eggs',
            'knights': 'ni'
        })
        self.assertEqual(options.options('foo'), suboptions)
        self.assertEqual(options.options('bar'), Options())

    def test_int(self):
        options = Options({
            'foo': '42',
            'bar': 'blub'
        })
        self.assertEqual(options.int('foo'), 42)
        self.assertEqual(options.int('bar'), 0)
        self.assertEqual(options.int('bar', 1), 1)
        self.assertEqual(options.int('baz'), 0)

    def test_float(self):
        options = Options({
            'foo': '42',
            'bar': 'blub'
        })
        self.assertEqual(options.float('foo'), 42.0)
        self.assertEqual(options.float('bar'), 0.0)

    def test_number(self):
        options = Options({
            'foo': '42',
            'bar': '43.5'
        })
        self.assertEqual(options.number('foo'), 42)
        self.assertEqual(options.number('bar'), 43.5)

    def test_str(self):
        options = Options({
            'foo': '42',
            'bar': 'blub'
        })
        self.assertEqual(options.str('foo'), '42')
        self.assertEqual(options.str('bar'), 'blub')
        self.assertEqual(options.str('baz', 'spam'), 'spam')
        self.assertEqual(options.str('baz'), '')

    def test_path(self):
        options = Options({
            'foo': 42,
            'bar': '~/tmp'
        })
        self.assertEqual(options.path('foo'), None)
        self.assertEqual(options.path('bar'), os.path.expanduser('~/tmp'))\
