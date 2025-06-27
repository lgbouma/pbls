"""
Utilities for a PBLS pipeline.

Contents:

Tarball management:
    create_tarball
    extract_tarball
    
ConfigParser pipeline management:
    save_status
    load_status
"""
#############
## LOGGING ##
#############
import logging
from pbls import log_sub, log_fmt, log_date_fmt

DEBUG = False
if DEBUG:
    level = logging.DEBUG
else:
    level = logging.INFO
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=level,
    style=log_sub,
    format=log_fmt,
    datefmt=log_date_fmt,
    force=True
)

LOGDEBUG = LOGGER.debug
LOGINFO = LOGGER.info
LOGWARNING = LOGGER.warning
LOGERROR = LOGGER.error
LOGEXCEPTION = LOGGER.exception

#############
## IMPORTS ##
#############
import os, tarfile
import configparser

def create_tarball(fullpaths, tarball_path):
    """
    Given a list of paths, write them into a gzipped tar achive.
    """
    with tarfile.open(tarball_path, "w:gz") as tar:
        for file_path in fullpaths:
            if os.path.isfile(file_path):
                tar.add(file_path, arcname=os.path.basename(file_path))
            else:
                LOGINFO(f"Warning: {file_path} is not a valid file.")
    LOGINFO(f"...Made {tarball_path}")


def extract_tarball(tarball_name, extract_path, verbose=1):
    """
    Unzip a gzipped tar archive.
    """
    with tarfile.open(tarball_name, "r:gz") as tar:
        tar.extractall(path=extract_path)
        if verbose:
            LOGINFO(f"Extracted {tarball_name} to {extract_path}")


def save_status(status_file, section, state_vars):
    """
    Save pipeline status

    Args:

        status_file (string): name of output file

        section (string): name of section to write

        state_vars (dict): dictionary of all options to populate the specified
        section
    """

    config = configparser.RawConfigParser()

    if os.path.isfile(status_file):
        config.read(status_file)

    if not config.has_section(section):
        config.add_section(section)

    for key, val in state_vars.items():
        config.set(section, key, val)

    with open(status_file, 'w') as f:
        config.write(f)


def load_status(status_file):
    """
    Load pipeline status

    Args:
        status_file (string): name of configparser file

    Returns:
        configparser.RawConfigParser
    """

    config = configparser.RawConfigParser()
    gl = config.read(status_file)

    return config