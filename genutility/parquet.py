from typing import Any, Callable, Dict, Iterable, TypeVar, Union

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
    "str": pa.string,
    "bool": pa.bool_,
}


def _to_pq_schema(d: Dict[str, Any], sort_keys: bool, outer: Callable[[list], T]) -> Union[T, pa.struct]:

    fields = []

    if sort_keys:
        keys: Iterable[str] = sorted(d)
    else:
        keys = d

    for k in keys:
        if isinstance(d[k], dict):
            fields.append((k, _to_pq_schema(d[k], sort_keys, pa.struct)))
        elif isinstance(d[k], list):
            if d[k]:
                if isinstance(d[k][0], dict):
                    fields.append((k, pa.list_(_to_pq_schema(d[k][0], sort_keys, pa.struct))))
                else:
                    fields.append((k, pa.list_(pqmap[d[k][0]]())))
        else:
            fields.append((k, pqmap[d[k]]()))

    return outer(fields)


def schema_simple_to_pq(schema: Dict[str, Any], sort_keys: bool = False) -> pa.schema:
    return _to_pq_schema(schema, sort_keys, pa.schema)
