"""Dependency injection and registration"""

class InjectionError(Exception):
    """Expection raise when a dependency injection error occurs."""
    pass

class Injector(object):
    """A class that manages factories and instantiates them on
    demand.
    """
    def __init__(self):
        self.factories = {}
        self.instances = {}
        self._instantiating = set()

    def get(self, name):
        """Get an instances for a factory name."""
        try:
            return self.instances[name]
        except KeyError:
            return self._instantiate(name)

    def _instantiate(self, name):
        if name in self._instantiating:
            raise InjectionError("factory '%s' depends on itself" % name)
        self._instantiating.add(name)
        try:
            depends, ctor = self.factories[name]
        except KeyError:
            raise InjectionError("factory '%s' has not been registered" % name)
        instance = ctor(*(self.get(depend) for depend in depends))
        self._instantiating.remove(name)
        self.instances[name] = instance
        return instance

    def register(self, name, depends):
        """Decorator to register a callable as a factory. Instantiated
        dependencies will be passed as arguments to the callable.
        """
        def decorator(cls):
            self.factories[name] = (depends, cls)
            return cls
        return decorator

injector = Injector()

def get(name):
    """Get an instances for a factory name from the global injector."""
    return injector.get(name)

def register(self, name, depends):
    """Register a class on the global injector."""
    return injector.register(name, depends)
