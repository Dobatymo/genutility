from __future__ import generator_stop

from functools import partial
from typing import Any, Iterable, List

from pyspark.sql import functions as f
from pyspark.sql import types as t
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


sparkmap = {
    "int64": t.LongType,
    "uint64": partial(t.DecimalType, 20, 0),
    "int32": t.IntegerType,
    "uint32": t.LongType,
    "str": t.StringType,
    "bool": t.BooleanType,
}


def schema_simple_to_spark(d: dict, sort_keys: bool = False) -> t.StructType:
    fields = []

    if sort_keys:
        keys: Iterable = sorted(d)
    else:
        keys = d

    for k in keys:
        if isinstance(d[k], dict):
            fields.append(t.StructField(k, schema_simple_to_spark(d[k], sort_keys)))
        elif isinstance(d[k], list):
            if d[k]:
                if isinstance(d[k][0], dict):
                    fields.append(t.StructField(k, t.ArrayType(schema_simple_to_spark(d[k][0], sort_keys))))
                else:
                    fields.append(t.StructField(k, t.ArrayType(sparkmap[d[k][0]]())))
        else:
            fields.append(t.StructField(k, sparkmap[d[k]]()))

    return t.StructType(fields)
