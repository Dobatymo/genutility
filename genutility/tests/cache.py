from pathlib import Path

from genutility.cache import cache
from genutility.test import MyTestCase, parametrize


def passthrough(x):
    return x


def passthrough_gen(x):
    yield x
    yield x


class CacheTest(MyTestCase):
    @parametrize(
        (None,),
        ("asd",),
        ({"1": 2, "3": 4},),
    )
    def test_cache(self, obj):
        path = Path("testtemp/pickle")
        cache(path, generator=False, serializer="pickle")(passthrough)(obj)
        result = cache(path, generator=False, serializer="pickle", cached_only=True)(passthrough)(obj)
        self.assertEqual(obj, result)

        path = Path("testtemp/msgpack")
        cache(path, generator=False, serializer="msgpack")(passthrough)(obj)
        result = cache(path, generator=False, serializer="msgpack", cached_only=True)(passthrough)(obj)
        self.assertEqual(obj, result)

        path = Path("testtemp/json")
        cache(path, generator=False, serializer="json")(passthrough)(obj)
        result = cache(path, generator=False, serializer="json", cached_only=True)(passthrough)(obj)
        self.assertEqual(obj, result)

        path = Path("testtemp/pickle-gen")
        list(cache(path, generator=True, serializer="pickle")(passthrough_gen)(obj))
        result = list(cache(path, generator=True, serializer="pickle", cached_only=True)(passthrough)(obj))
        self.assertEqual([obj, obj], result)

        path = Path("testtemp/msgpack-gen")
        list(cache(path, generator=True, serializer="msgpack")(passthrough_gen)(obj))
        result = list(cache(path, generator=True, serializer="msgpack", cached_only=True)(passthrough)(obj))
        self.assertEqual([obj, obj], result)

        path = Path("testtemp/json-gen")
        list(cache(path, generator=True, serializer="json")(passthrough_gen)(obj))
        result = list(cache(path, generator=True, serializer="json", cached_only=True)(passthrough)(obj))
        self.assertEqual([obj, obj], result)


if __name__ == "__main__":
    import unittest

    unittest.main()
