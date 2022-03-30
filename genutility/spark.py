from __future__ import generator_stop

from typing import Any, Iterable, List

import pyspark.sql.functions as f
from pyspark.sql.column import Column
from pyspark.sql.dataframe import DataFrame


def timestamp_from_unixtime_ms(colname: str) -> Column:
    """Probably requires Spark>=3.0.0"""

    dt = f.from_unixtime(f.col(colname) / 1000).cast("timestamp")
    msec = f.expr("INTERVAL 1 milliseconds") * (f.col(colname) % 1000)
    return (dt + msec).alias(colname)


def null_columns(df: DataFrame) -> List[str]:
    """Return a list of column names of columns which are only ever have null."""

    df_count = df.count()
    null_counts = df.select([f.count(f.when(f.col(c).isNull(), c)).alias(c) for c in df.columns]).collect()[0].asDict()
    return [k for k, v in null_counts.items() if v >= df_count]


def drop_null_columns(df: DataFrame) -> DataFrame:
    """Drop all columns from dataframe which are only ever null."""

    to_drop = null_columns(df)
    return df.drop(*to_drop)


def lit_array(it: Iterable[Any]) -> Column:
    """Create a Pyspark array of literal values."""

    return f.array(list(map(f.lit, it)))
