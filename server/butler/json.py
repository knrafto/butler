import simplejson as json

class DefaultEncoder(json.JSONEncoder):
    """The default JSON encoder. When encoding objects, if the object
    has a :attribute:json property, it will be used instead of the
    object.
    """
    def __init__(self, **kwds):
        defaults = {
            'indent': 4,
            'separators': (',', ': ')
        }
        defaults.update(kwds)
        super(DefaultEncoder, self).__init__(**defaults)

    def default(self, obj):
        try:
            encode = obj.json
        except AttributeError:
            return super(DefaultEncoder, self).default(obj)
        else:
            return encode()

defaultEncoder = DefaultEncoder()

def loads(obj):
    return json.loads(obj)

def dumps(obj):
    return defaultEncoder.encode(obj)

def iterencode(obj):
    return defaultEncoder.iterencode(obj)

