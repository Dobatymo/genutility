from __future__ import generator_stop

import struct


def bitness():
    return struct.calcsize("P") * 8
