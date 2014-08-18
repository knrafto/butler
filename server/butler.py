#!/usr/bin/env python
from __future__ import print_function

import json
import os
import sys

import gevent
import gevent.wsgi

from endpoint import Dispatcher
from plugin import find_plugins, start_plugins

default_config_path = \
    os.path.expanduser(os.path.join('~', '.config', 'butler', 'butler.cfg'))

def load_config(path):
    config = {}
    try:
        with open(path, 'r') as config_file:
            config = json.load(config_file)
    except (IOError, ValueError) as e:
        print(e, file=sys.stderr)
    return config

def serve(config_path):
    config = load_config(config_path)
    try:
        address = config['server']['address']
    except KeyError:
        address = '127.0.0.1:80'
    plugins = find_plugins('plugins')
    delegates = start_plugins(plugins, config)
    server = gevent.wsgi.WSGIServer(address, Dispatcher(delegates))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    config_path = default_config_path
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    serve(config_path)
