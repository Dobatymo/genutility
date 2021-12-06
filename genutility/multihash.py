from __future__ import generator_stop

from functools import reduce

import rhash

from .file import blockfileiter
from .hash import FILE_IO_BUFFER_SIZE
from .ops import bit_or


def multi_hash_file(path, hash_types, base=None, mode="rb", encoding=None, errors=None, chunk_size=FILE_IO_BUFFER_SIZE):

    """Hashes `path` with multiple hash functions.
    `hash_types` is a list of names, eg. ("CRC32", "SHA1").
    """

    hashdict = {
        "CRC32": rhash.CRC32,
        "MD4": rhash.MD4,
        "MD5": rhash.MD5,
        "SHA1": rhash.SHA1,
        "TIGER": rhash.TIGER,
        "TTH": rhash.TTH,
        "BTIH": rhash.BTIH,
        "ED2K": rhash.ED2K,
        "AICH": rhash.AICH,
        "WHIRLPOOL": rhash.WHIRLPOOL,
        "RIPEMD-160": rhash.RIPEMD160,
        "GOST12_256": rhash.GOST12_256,
        "GOST12_512": rhash.GOST12_512,
        "GOST94": rhash.GOST94,
        "GOST94_CRYPTOPRO": rhash.GOST94_CRYPTOPRO,
        "HAS-160": rhash.HAS160,
        "SNEFRU-128": rhash.SNEFRU128,
        "SNEFRU-256": rhash.SNEFRU256,
        "SHA-224": rhash.SHA224,
        "SHA-256": rhash.SHA256,
        "SHA-384": rhash.SHA384,
        "SHA-512": rhash.SHA512,
        "EDON-R256": rhash.EDONR256,
        "EDON-R512": rhash.EDONR512,
    }

    basedict = {
        "upper": rhash.RHPR_UPPERCASE,
        "raw": rhash.RHPR_RAW,
        "hex": rhash.RHPR_HEX,
        "HEX": rhash.RHPR_HEX | rhash.RHPR_UPPERCASE,
        "base32": rhash.RHPR_BASE32,
        "BASE32": rhash.RHPR_BASE32 | rhash.RHPR_UPPERCASE,
        "base64": rhash.RHPR_BASE64,
    }

    hashlist = tuple(hashdict[i.upper()] for i in hash_types)
    flags = basedict.get(base, 0)

    hasher = rhash.RHash(reduce(bit_or, hashlist))
    for data in blockfileiter(path, mode, encoding, errors, chunk_size=chunk_size):
        hasher.update(data)
    hasher.finish()
    return tuple(hasher._print(i, flags) for i in hashlist)


if __name__ == "__main__":
    import argparse

    funcs = (
        "CRC32",
        "MD4",
        "MD5",
        "SHA1",
        "TIGER",
        "TTH",
        "BTIH",
        "ED2K",
        "AICH",
        "WHIRLPOOL",
        "RIPEMD-160",
        "GOST12_256",
        "GOST12_512",
        "GOST94",
        "GOST94_CRYPTOPRO",
        "HAS-160",
        "SNEFRU-128",
        "SNEFRU-256",
        "SHA-224",
        "SHA-256",
        "SHA-384",
        "SHA-512",
        "EDON-R256",
        "EDON-R512",
    )

    parser = argparse.ArgumentParser(
        description="Multi file hashing", epilog="Example: multihash C:\\Windows\\System32\\calc.exe -f CRC32 SHA1"
    )
    parser.add_argument(
        "-f",
        "--hashfuncs",
        nargs="+",
        help="list of hash functions. Can be one or more of: {}".format(", ".join(funcs)),
        required=True,
    )
    parser.add_argument("file", metavar="FILE", help="path to the file")
    args = parser.parse_args()
    print("\n".join(f"{i}: {j}" for i, j in zip(args.hashfuncs, multi_hash_file(args.file, args.hashfuncs))))
