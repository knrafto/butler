"""Plugins and dependency injection."""
import inspect

from werkzeug.utils import find_modules, import_string

class Plugin(object):
    """Plugin base class.

    A plugin should define its name and the names of its dependencies.
    The constructor will be passed its dependencies and any
    configuration arguments.
    """
    name = ''
    depends = ()

def topsort(G):
    """Sort a graph in dependency order.

    >>> topsort({
    ...     1: [],
    ...     2: [1],
    ...     3: [2],
    ...     4: [3, 2],
    ...     5: [4]
    ... })
    [5, 4, 3, 2, 1]
    >>> topsort({
    ...     1: [2],
    ...     2: [1]
    ... })
    Traceback (most recent call last):
        ...
    ValueError: Cyclic dependencies
    """
    count = dict((u, 0) for u in G)
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
            if count[v] == 0:
                Q.append(v)
    if len(S) != len(G):
        raise ValueError('Cyclic dependencies')
    return S

def start_plugins(plugins, config):
    """Create a list of plugins. Returns a dictionary of plugin names
    and the created objects. Config should be a dictionary of plugin
    name to configuration options.

    >>> config = {
    ...     'spam': {'foo': 1},
    ...     'eggs': {'bar': 2}
    ... }
    >>> class Spam(Plugin):
    ...     name = 'spam'
    ...     def __init__(self, foo=0, **kwds):
    ...         self.foo = foo
    ...
    >>> class Eggs(Plugin):
    ...     name = 'eggs'
    ...     depends = ['spam']
    ...     def __init__(self, spam, **kwds):
    ...         self.foo = spam.foo
    ...         self.bar = kwds['bar']
    ...
    >>> plugins = start_plugins([Spam, Eggs], config)
    >>> plugins['spam'].foo
    1
    >>> plugins['eggs'].foo
    1
    >>> plugins['eggs'].bar
    2
    """
    plugins = {plugin.name: plugin for plugin in plugins}
    graph = {name: plugin.depends for name, plugin in plugins.items()}
    started = {}
    for name in reversed(topsort(graph)):
        plugin = plugins[name]
        args = [started[dep] for dep in plugin.depends]
        kwds = config.get(name, {})
        started[name] = plugin(*args, **kwds)
    return started

def find_plugins(import_path, recursive=False):
    """Find all plugins below an import path."""
    for module_path in find_modules(import_path, recursive=recursive):
        module = import_string(module_path)
        for _, plugin in inspect.getmembers(
                module,
                lambda a: inspect.isclass(a) and issubclass(a, Plugin)):
            yield plugin

