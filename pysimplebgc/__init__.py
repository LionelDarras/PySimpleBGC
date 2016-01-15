# -*- coding: utf-8 -*-
'''
    pysimplebgc
    -----------

    The public API and command-line interface to PySimpleBGC package.

    :copyright: Copyright 2015 Lionel Darras and contributors, see AUTHORS.
    :license: GNU GPL v3.

'''
# Make sure the logger is configured early:
from .logger import LOGGER, active_logger
from .device import SimpleBGC32

VERSION = '0.1dev'
__version__ = VERSION
