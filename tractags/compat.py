# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, Steffen Hoffmann
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

"""Various classes and functions to provide backwards-compatibility with
previous versions of Python from 2.4 and Trac from 0.11 onwards.
"""

try:
    from trac.util.datefmt import to_utimestamp
    from trac.util.datefmt import to_datetime
except ImportError:
    # Cheap fallback for Trac 0.11 compatibility.
    from trac.util.datefmt  import to_timestamp
    def to_utimestamp(dt):
        return to_timestamp(dt) * 1000000L

    from trac.util.datefmt import to_datetime as to_dt
    def to_datetime(ts):
        return to_dt(ts / 1000000)
