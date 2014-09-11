#!/usr/bin/env python
import os
import simplejson as json

import gevent

import butler

if __name__ == '__main__':
    config_path = os.path.expanduser(
        os.path.join('~', '.config', 'butler', 'butler.cfg'))
    with open(config_path) as config_file:
        config = json.load(config_file)
    butler.Butler(config).find('servants')
    gevent.wait()
