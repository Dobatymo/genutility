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


def pl_islice(df: pl.DataFrame, start: Optional[int], stop: Union[int, Type[_Unset], None] = _Unset) -> pl.DataFrame:
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
    "NoneType": pl.Null,
    "int8": pl.Int8,
    "uint8": pl.UInt8,
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


def _to_polars_dtype(
    value: Any,
    sort_keys: bool,
    float_bits: Literal[32, 64],
    min_int_bits: Optional[Literal[8, 16, 32, 64]],
) -> Any:
    if isinstance(value, dict):
        return pl.Struct(_to_polars_schema(value, sort_keys, float_bits, min_int_bits))
    elif isinstance(value, list):
        return pl.List(_to_polars_dtype(value[0], sort_keys, float_bits, min_int_bits) if value else pl.Null)
    elif value == "float":
        return pl.Float32 if float_bits == 32 else pl.Float64

    dtype = plmap[value]
    if min_int_bits is not None and value.startswith(("int", "uint")):
        unsigned = value.startswith("uint")
        bits = int(value[4:] if unsigned else value[3:])
        if bits < min_int_bits:
            dtype = plmap[f"{'uint' if unsigned else 'int'}{min_int_bits}"]
    return dtype


def _to_polars_schema(
    d: Dict[str, Any],
    sort_keys: bool,
    float_bits: Literal[32, 64],
    min_int_bits: Optional[Literal[8, 16, 32, 64]],
) -> Dict[str, Any]:
    keys = sorted(d) if sort_keys else d
    return {key: _to_polars_dtype(d[key], sort_keys, float_bits, min_int_bits) for key in keys}


def schema_simple_to_polars(
    schema: Dict[str, Any],
    sort_keys: bool = False,
    float_bits: Literal[32, 64] = 64,
    *,
    min_int_bits: Optional[Literal[8, 16, 32, 64]] = None,
) -> pl.Schema:
    """Convert a simple schema to a Polars ``Schema``.

    ``NoneType`` and empty lists are retained as Null and List(Null).
    ``min_int_bits`` sets a minimum integer width throughout nested schemas,
    preserving signedness and larger widths. By default, integer widths are
    unchanged.
    """

    if float_bits not in (32, 64):
        raise ValueError("float_bits must be 32 or 64")
    if min_int_bits not in (None, 8, 16, 32, 64):
        raise ValueError("min_int_bits must be None, 8, 16, 32 or 64")
    return pl.Schema(_to_polars_schema(schema, sort_keys, float_bits, min_int_bits))
