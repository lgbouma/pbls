import os, socket
from pbls import __path__
from os.path import join

VERBOSE = 0

# cache for temporary files
CACHEDIR = join(os.path.expanduser("~"), ".pbls_cache")
if not os.path.exists(CACHEDIR): os.mkdir(CACHEDIR)

# data storage directory
DATADIR = os.path.join(os.path.dirname(__path__[0]), 'data')