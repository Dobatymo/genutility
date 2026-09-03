from typing import Any, Dict, Literal, Optional, Type, Union

import numpy as np
import polars as pl
from typing_extensions import final


@final
class _Unset:
    pass


def pl_index(df: pl.DataFrame, indices: np.ndarray, index_col: str = "index") -> pl.DataFrame:
    assert index_col not in df.columns

    return (
        df.with_row_index(index_col)
        .join(
            pl.DataFrame({index_col: indices}),
            on=index_col,
            how="inner",
            validate="1:1",
            maintain_order="left",
        )
        .drop(index_col)
    )


def pl_islice(df: pl.DataFrame, start: Optional[int], stop: Union[int, None, Type[_Unset]] = _Unset) -> pl.DataFrame:
    if start is None and stop is None:
        return df
    elif stop is _Unset:
        return df.slice(0, start)
    elif start is None:
        return df.slice(0, stop)
    elif stop is None:
        return df.slice(start, None)
    else:
        return df.slice(start, stop - start)


plmap = {
    "int64": pl.Int64,
    "uint64": pl.UInt64,
    "int32": pl.Int32,
    "uint32": pl.UInt32,
    "int16": pl.Int16,
    "uint16": pl.UInt16,
    "float": pl.Float64,
    "str": pl.String,
    "bool": pl.Boolean,
}


def _to_polars_schema(d: Dict[str, Any], sort_keys: bool, float_bits: Literal[32, 64]) -> Dict[str, Any]:
    fields = {}
    keys = sorted(d) if sort_keys else d
    for k in keys:
        value = d[k]
        if isinstance(value, dict):
            fields[k] = pl.Struct(_to_polars_schema(value, sort_keys, float_bits))
        elif isinstance(value, list):
            if value:
                item = value[0]
                if isinstance(item, dict):
                    fields[k] = pl.List(pl.Struct(_to_polars_schema(item, sort_keys, float_bits)))
                else:
                    fields[k] = pl.List(pl.Float32 if item == "float" and float_bits == 32 else plmap[item])
        else:
            fields[k] = pl.Float32 if value == "float" and float_bits == 32 else plmap[value]
    return fields


def schema_simple_to_polars(
    schema: Dict[str, Any], sort_keys: bool = False, float_bits: Literal[32, 64] = 64
) -> pl.Schema:
    """Convert a simple schema to a Polars ``Schema``."""

    if float_bits not in (32, 64):
        raise ValueError("float_bits must be 32 or 64")
    return pl.Schema(_to_polars_schema(schema, sort_keys, float_bits))
