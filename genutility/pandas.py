from __future__ import generator_stop

from typing import Any, Callable, Iterable, List, Optional, Tuple, TypeVar

from pandas import DataFrame, Series

from .func import identity

T = TypeVar("T")


def intersect_columns(*dfs: DataFrame, sort=False) -> Tuple[DataFrame, ...]:

    """Takes multiple dataframes and removes the columns which are not present in the other dataframes.
    The order of columns will be equalized.
    """

    cols = tuple(set(df.columns) for df in dfs)
    goodset = set.intersection(*cols)
    if sort:
        good = sorted(goodset)
    else:
        good = list(goodset)
    dfs = tuple(df[good] for df in dfs)
    assert len(set(map(lambda df: tuple(df.columns), dfs))) == 1

    return dfs


def pandas_json(obj):
    # type: (Any, ) -> Any

    """Can be used for the `json.dump` `default` argument
    to make some pandas objects JSON serializable.
    """

    if isinstance(obj, DataFrame):
        return dict(obj)
    elif isinstance(obj, Series):
        return tuple(obj)

    raise TypeError(f"object of type {type(obj)} cannot be JSON serialized: {obj}")


def strlist(sep):
    # type: (str, ) -> Callable[[str], List[str]]

    def inner(s):
        if s:
            return s.split(sep)
        else:
            return []

    return inner


def dataframe_to_dict(df, empty=False, cellfunc=None, dictcls=dict):
    # type: (DataFrame, bool, Optional[Callable], Callable[[Iterable[Tuple[str, Any]]], T]) -> T

    """Turns dataframes into trees. Columns first, then rows"""

    if cellfunc is None:
        cellfunc = identity

    def cols(series):
        for rowname, rowdata in series.iteritems():
            value = cellfunc(rowdata)
            if value or empty:
                yield rowname, value

    def rows(df):
        for colname, coldata in df.iteritems():
            value = dictcls(cols(coldata))
            if value or empty:
                yield colname, value

    return dictcls(rows(df))
