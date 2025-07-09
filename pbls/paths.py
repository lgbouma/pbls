import os, socket
from pbls import __path__
from os.path import join

VERBOSE = 0

# cache for temporary files
CACHEDIR = join(os.path.expanduser("~"), ".pbls_cache")
if not os.path.exists(CACHEDIR): os.mkdir(CACHEDIR)

hostname = socket.gethostname()
if hostname in ['wh1', 'wh2', 'wh3', 'marduk.local']:
    DATADIR = join(__path__[0], 'data')
    RESULTSDIR = join(os.path.dirname(__path__[0]), 'results')
    TESTRESULTSDIR = join(RESULTSDIR, 'tests')
    TABLEDIR = join(RESULTSDIR, 'tables')

    for l in [DATADIR, RESULTSDIR, TESTRESULTSDIR, TABLEDIR]:
        if not os.path.exists(l):
            if VERBOSE:
                print(f"Making {l}")
            os.mkdir(l)