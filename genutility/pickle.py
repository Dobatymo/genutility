import importlib
import logging
import pickle  # nosec
from typing import Any, Iterable, Iterator, Optional, Tuple

from ._files import PathType
from .atomic import sopen
from .file import copen

logger = logging.getLogger(__name__)


def read_pickle(path: PathType) -> Any:
    """Read pickle file from `path`.
    Warning: All usual security consideration regarding the pickle module still apply.
    """

    with copen(path, "rb") as fr:
        return pickle.load(fr)  # nosec


def write_pickle(result: Any, path: PathType, protocol: Optional[int] = None, safe: bool = False) -> None:
    """Write `result` to `path` using pickle serialization.

    `protocol': pickle protocol version
    `safe`: if True, don't overwrite original file in case any error occurs
    """

    with sopen(path, "wb", safe=safe) as fw:
        pickle.dump(result, fw, protocol=protocol)


def read_iter(path: PathType) -> Iterator[Any]:
    """Read pickled iterable from `path`.
    Warning: All usual security consideration regarding the pickle module still apply.
    """

    with copen(path, "rb") as fr:
        unpickler = pickle.Unpickler(fr)  # nosec
        while fr.peek(1):
            yield unpickler.load()


def write_iter(it: Iterable[Any], path: PathType, protocol: Optional[int] = None, safe: bool = False) -> Iterator[Any]:
    """Write iterable `it` to `path` using pickle serialization. This uses much less memory than
            writing a full list at once.
    Read back using `read_iter()`. If `safe` is True, the original file is not overwritten
            if any error occurs.
    This is a generator which yields the values read from `it`. So it must be consumed
            to actually write anything to disk.
    """

    with sopen(path, "wb", safe=safe) as fw:
        pickler = pickle.Pickler(fw, protocol=protocol)
        for result in it:
            pickler.dump(result)
            yield result


def key_to_hash(key: Any, protocol: Optional[int] = None) -> str:
    from hashlib import md5

    binary = pickle.dumps(key, protocol=protocol)
    return md5(binary).hexdigest()  # nosec


def unpickle(path: PathType, requirements: Iterable[Tuple[str, Optional[str]]] = ()) -> Any:
    """Can be used to unpickle objects when normal unpickling fails to import some dependencies correctly.
    path: Path to the pickled file.
    requirements: Iterable of (module, package) tuples to be imported.

    Consider this scenario:
    ```python
    import pickle
    class asd:
            def qwe():
                    pass
    a = asd()
    with open("asd.p", "wb") as fw:
            pickle.dump(a, fw)

    with open("asd.p", "rb") as fr:
            a = pickle.load(fr)  # everything ok here
    ```

    Now the class definition is moved out of this file into another file `qwe.py`. Then
    ```python
    import pickle
    with open("asd.p", "rb") as fr:
            a = pickle.load(fr)  # AttributeError: Can't get attribute 'asd' on <module '__main__' (built-in)>
    ```

    Now unpickle can be used to fix this problem:
    ```python
    from genutility.pickle import unpickle
    a = unpickle("asd.p", [("qwe", "asd")])
    ```

    Warning: Only use on safe inputs.
    """

    import __main__

    for module, package in requirements:
        mod = importlib.import_module(module, package)
        if package:
            name = package
            type = getattr(mod, package)
        else:
            name = module
            type = mod

        setattr(__main__, name, type)

    with copen(path, "rb") as fr:
        return pickle.load(fr)  # nosec
