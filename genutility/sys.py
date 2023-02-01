import struct


def bitness():
    return struct.calcsize("P") * 8
