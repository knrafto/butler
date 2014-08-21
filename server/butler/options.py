class Options(dict):
    def __init__(self, value=None):
        try:
            super(Options, self).__init__(value)
        except Exception:
            super(Options, self).__init__()

    def get(self, key, default=None, type=None):
        try:
            r = self[key]
            if type:
                r = type(r)
        except (KeyError, TypeError, ValueError):
            r = default
        return r

    def options(self, key):
        return self.get(key, Options(), Options)

    def int(self, key, default=0):
        return self.get(key, default, int)

    def float(self, key, default=0.0):
        return self.get(key, default, float)

    def number(self, key, default=0):
        return self.int(key, default) or self.float(key, default)

    def str(self, key, default=''):
        return self.get(key, default, str)

    def bool(self, key, default=False):
        return self.get(key, default, bool)
