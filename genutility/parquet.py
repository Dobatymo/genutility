from typing import Any, Callable, Dict, Iterable, Literal, TypeVar, Union

import pyarrow as pa
from pyarrow import parquet as pq

T = TypeVar("T")


def table_dumps(table: pa.Table) -> bytes:
    writer = pa.BufferOutputStream()
    pq.write_table(table, writer)
    return bytes(writer.getvalue())


def table_loads(table: bytes) -> pa.Table:
    reader = pa.BufferReader(table)
    return pq.read_table(reader)


def schema_dumps(schema: pa.schema) -> bytes:
    writer = pa.BufferOutputStream()
    pq.write_metadata(schema, writer)
    return bytes(writer.getvalue())


pqmap = {
    "int64": pa.int64,
    "uint64": pa.uint64,
    "int32": pa.int32,
    "uint32": pa.uint32,
    "int16": pa.int16,
    "uint16": pa.uint16,
    "float": pa.float64,
    "str": pa.string,
    "bool": pa.bool_,
}


def _pq_type(name: str, float_bits: Literal[32, 64]) -> Callable[[], pa.DataType]:
    if name == "float":
        return pa.float32 if float_bits == 32 else pa.float64
    return pqmap[name]


def _to_pq_schema(
    d: Dict[str, Any], sort_keys: bool, outer: Callable[[list], T], float_bits: Literal[32, 64]
) -> Union[T, pa.struct]:
    fields = []

    if sort_keys:
        keys: Iterable[str] = sorted(d)
    else:
        keys = d

    for k in keys:
        if isinstance(d[k], dict):
            fields.append((k, _to_pq_schema(d[k], sort_keys, pa.struct, float_bits)))
        elif isinstance(d[k], list):
            if d[k]:
                if isinstance(d[k][0], dict):
                    fields.append((k, pa.list_(_to_pq_schema(d[k][0], sort_keys, pa.struct, float_bits))))
                else:
                    fields.append((k, pa.list_(_pq_type(d[k][0], float_bits)())))
        else:
            fields.append((k, _pq_type(d[k], float_bits)()))

    return outer(fields)


def schema_simple_to_pq(schema: Dict[str, Any], sort_keys: bool = False, float_bits: Literal[32, 64] = 64) -> pa.schema:
    if float_bits not in (32, 64):
        raise ValueError("float_bits must be 32 or 64")
    return _to_pq_schema(schema, sort_keys, pa.schema, float_bits)
