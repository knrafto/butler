import collections
import inspect

import werkzeug.utils

class EventEmitter(object):
    """A mixin that provides the ability to emit and listen for
    events.
    """
    def __init__(self):
        self._callbacks = collections.defaultdict(list)

    def emit(self, event, *args, **kwds):
        """Emit an event."""
        for f in self._callbacks[event][:]:
            f(*args, **kwds)

    def on(self, event, f):
        """Register a listener for an event."""
        self._callbacks[event].append(f)

    def off(self, event, f):
        """Unregister a listener for an event."""
        if f in self._callbacks[event]:
            self._callbacks[event].remove(f)

    def listeners(self, event):
        """Return the listeners for an event."""
        return self._callbacks[event]

class Butler(EventEmitter):
    """The butler hires and manages all servants.
    Initialize with a configuration dictionary.
    """
    def __init__(self, config):
        self.config = config
        self.servants = {}
        super(Butler, self).__init__()

    def get(self, name):
        return self.servants[name]

    def hire(self, servant_class):
        """Hire a servant from a class."""
        name = servant_class.name
        config = self.config.get(name, None)
        self.servants[name] = servant_class(self, config)

    def call(self, method, *args, **kwds):
        """Call a method on another servant."""
        servant_name, method_name = method.rsplit('.', 1)
        if method_name.startswith('_'):
            raise ValueError("cannot call hidden method '%s'" % method)
        return getattr(self.servants[servant_name], method_name)(*args, **kwds)

    def find(self, import_path):
        for module_name in werkzeug.utils.find_modules(import_path):
            module = werkzeug.utils.import_string(module_name)
            for _, cls in inspect.getmembers(module,
                    lambda cls: inspect.isclass(cls) and
                    issubclass(cls, Servant)):
                self.hire(cls)

class Servant(object):
    """A domestic servant."""
    name = ''

    def __init__(self, butler, config):
        self.butler = butler
        self.config = config

    def emit(self, event, *args, **kwds):
        """Emit an event to the household."""
        self.butler.emit(event, *args, **kwds)

    def call(self, method, *args, **kwds):
        """Call a method on another servant."""
        return self.butler.call(method, *args, **kwds)

    def on(self, event, f):
        """Register a listener for an event."""
        self.butler.on(event, f)

    def off(self, event, f):
        """Unregister a listener for an event."""
        self.butler.off(event, f)
