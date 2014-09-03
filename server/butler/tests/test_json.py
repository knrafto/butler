import unittest

from butler import json

class Spam(object):
    def json(self):
        return Eggs()

class Eggs(object):
    def json(self):
        return 'eggs'

class JSONTestCase(unittest.TestCase):
    def test_dumps(self):
        self.assertEqual(json.dumps(Spam()), '"eggs"')

    def test_iterencode(self):
        result = ''.join(json.iterencode(Spam()))
        self.assertEqual(result, '"eggs"')

    def test_loads(self):
        self.assertEqual(
            json.loads('{"spam": "eggs", "knights": "ni"}'),
            {
                'spam': 'eggs',
                'knights': 'ni'
            })
