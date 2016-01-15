# coding: utf8
"""
    pysimplebgc.compat
    -------------------

    Workarounds for compatibility with Python 3.x in the same code base.

    :copyright: Copyright 2015 Lionel Darras and contributors, see AUTHORS.
    :license: GNU GPL v3.

"""

import sys

# -------
# Pythons
# -------

# Syntax sugar.
_ver = sys.version_info

#: Python 3.x?
is_py3 = (_ver[0] == 3)

#: Python 3.0.x
is_py30 = (is_py3 and _ver[1] == 0)

#: Python 3.1.x
is_py31 = (is_py3 and _ver[1] == 1)

#: Python 3.2.x
is_py32 = (is_py3 and _ver[1] == 2)

#: Python 3.3.x
is_py33 = (is_py3 and _ver[1] == 3)

#: Python 3.4.x
is_py34 = (is_py3 and _ver[1] == 4)

# ---------
# Specifics
# ---------

if is_py3:
    from logging import NullHandler
    from collections import OrderedDict
    from io import StringIO

    def to_char(string):
        if len(string) == 0:
            return str('')
        return str(string[0])

    str = str
    bytes = bytes
    stdout = sys.stdout
    xrange = range
