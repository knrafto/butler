#!/usr/bin/env python
from __future__ import print_function

import os
import sys

import gevent
import gevent.wsgi
import simplejson as json

from butler import service
from butler.options import Options
from butler.routing import Dispatcher

default_config_path = \
    os.path.expanduser(os.path.join('~', '.config', 'butler', 'butler.cfg'))

def load_config(path):
    try:
        with open(path, 'r') as config_file:
            return Options(json.load(config_file))
    except (IOError, TypeError, ValueError) as e:
        print(e, file=sys.stderr)

def serve(config_path):
    options = load_config(config_path)
    services = list(service.find_all('butler.services'))
    services.append(service.static('config', options))
    delegates = service.start(services)
    address = options.options('server').str('address', '127.0.0.1:8000')
    server = gevent.wsgi.WSGIServer(address, Dispatcher(delegates))
    server.serve_forever()

def main():
    config_path = default_config_path
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    serve(config_path)
