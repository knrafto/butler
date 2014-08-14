#!/usr/bin/env python
from __future__ import print_function

import json
import os
import sys

import gevent
import gevent.wsgi

default_config_path =
    os.path.expanduser(os.path.join('~', '.config', 'butler', 'butler.cfg')))

def load_config(path):
    config = {}
    try:
        with open(path, 'r') as config_file:
            config = json.load(config_file)
    except (IOError, ValueError) as e:
        print(e, file=sys.stderr)
    return config

def create_server(config, address='127.0.0.1:80'):
    pass

def serve(config_path):
    config = load_config(config_path)
    server_config = config.get('server', {})
    server = create_server(config, **server_config)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    config_path = default_config_path
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    serve(config_path)
