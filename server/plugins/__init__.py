from libspotify import Spotify

all_plugins = [Spotify]

def start(config):
    def start_plugin(plugin):
        name = plugin.plugin_name
        kwds = config.get(name, {})
        return plugin(**kwds)
    return {
        plugin.plugin_name: start_plugin(plugin) for plugin in all_plugins
    }
