"""
This module contains paths that are re-used throughout the project.  Crucially,
it makes a hidden local cache directory, at ~/.pbls_cache, where results from
large batch runs will by default be stored.
"""
import os
from os.path import join
from pbls import __path__
__path__ = list(__path__)

RESULTSDIR = join(os.path.dirname(__path__[0]), 'results')

TESTRESULTSDIR = join(RESULTSDIR, 'tests')

TABLEDIR = join(RESULTSDIR, 'tables')

CACHEDIR = join(os.path.expanduser('~'), '.pbls_cache')

PAPERDIR = join(os.path.dirname(__path__[0]), 'papers', 'paper')

DATADIR = join(__path__[0], 'data')

SECRETDATADIR = join(os.path.dirname(__path__[0]), 'secret_data')

for l in [DATADIR, CACHEDIR, RESULTSDIR, TABLEDIR, TESTRESULTSDIR]:
    if not os.path.exists(l):
        print(f"Making {l}")
        os.mkdir(l)

# used for making non-reusable functionality
LOCALDIR = join(os.path.expanduser('~'), 'local')
if not os.path.exists(LOCALDIR):
    print(f"Did not find {l}; continuing anyway.")
