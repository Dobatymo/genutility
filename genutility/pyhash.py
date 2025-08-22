from typing import Union


def _to_pysigned(x: int, bits: int) -> int:
    mask = (1 << bits) - 1
    x &= mask
    signbit = 1 << (bits - 1)
    return x - (1 << bits) if x & signbit else x


def py2_hash_ucs_4(data: Union[str, bytes], bits: int = 64) -> int:
    if not isinstance(data, (str, bytes)):
        raise ValueError("only str and bytes are supported")

    if bits not in (32, 64):
        raise ValueError("only 32 or 64 bits are supported")

    if not data:
        return 0

    if isinstance(data, str):
        x = ord(data[0]) << 7
        for cp in map(ord, data):
            x = (1000003 * x) ^ cp
    elif isinstance(data, bytes):
        x = data[0] << 7
        for b in data:
            x = (1000003 * x) ^ b
    else:
        assert False

    x ^= len(data)
    x = _to_pysigned(x, bits)
    if x == -1:
        x = -2
    return x
