from __future__ import generator_stop

import pyspark.sql.functions as f
from pyspark.sql.column import Column


def timestamp_from_unixtime_ms(colname: str) -> Column:
    """ Probably requires Spark>=3.0.0 """

    dt = f.from_unixtime(f.col(colname) / 1000).cast("timestamp")
    msec = f.expr("INTERVAL 1 milliseconds") * (f.col(colname) % 1000)
    return (dt + msec).alias(colname)
