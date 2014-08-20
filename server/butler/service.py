"""Plugins and dependency injection."""
import collections
import inspect

from werkzeug.utils import find_modules, import_string

class DependencyError(ValueError):
    """Signals a missing or cyclic dependency."""
    pass

class Service(object):
    """A named service. Services may depend on other services, and
    these names will be injected into the service upon creation.

    :param name: the service name
    :param depends: a sequence of service names
    :param init: a function that will construct the service.
                 Resolved dependencies will be passed to the functions
                 as arguments in the order they are listed.
    """
    def __init__(self, name, depends, init):
        self.name = name
        self.depends = depends
        self.init = init

    def __call__(self, *args, **kwds):
        return self.init(*args, **kwds)

    def create(self, services):
        """Instantiate a service, using the dictionary to resolve
        dependencies.

        :param services: a dictionary of already-created services.
        """
        args = []
        for dep_name in self.depends:
            try:
                dep = services[dep_name]
            except KeyError:
                raise DependencyError("missing dependency '%s' for '%s'" %
                                      (self.name, dep_name))
            args.append(dep)
        return self.init(*args)

    def __repr__(self):
        return "<Service '%s'>" % self.name

def static(name, obj):
    """A static object that depends on nothing else."""
    return Service(name, (), lambda: obj)

def singleton(cls):
    """A decorator to create a singleton service from a class
    definition. The class's constructor will be used as the
    service constructor.
    """
    return Service(cls.name, cls.depends, cls)

def topsort(G):
    """Sort a graph in dependency order."""
    count = collections.defaultdict(int)
    for u in G:
        for v in G[u]:
            count[v] += 1
    Q = [u for u in G if count[u] == 0]
    S = []
    while Q:
        u = Q.pop()
        S.append(u)
        for v in G[u]:
            count[v] -= 1
            if v in G and count[v] == 0:
                Q.append(v)
    if len(S) != len(G):
        raise DependencyError('Cyclic dependencies')
    return S

def start(services):
    """Start a sequence of services. Returns a dictionary of service
    names to the created instances.
    """
    services = {service.name: service for service in services}
    graph = {name: service.depends for name, service in services.items()}
    started = {}
    for name in reversed(topsort(graph)):
        started[name] = services[name].create(started)
    return started

def find_all(import_path, recursive=False):
    """Find all plugins below an import path."""
    for module_path in find_modules(import_path, recursive=recursive):
        module = import_string(module_path)
        for _, service in inspect.getmembers(
                module, lambda a: isinstance(a, Service)):
            yield service
