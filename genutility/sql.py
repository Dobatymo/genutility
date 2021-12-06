from __future__ import generator_stop

from itertools import chain, repeat
from typing import TYPE_CHECKING

from .exceptions import InconsistentState, NoResult

if TYPE_CHECKING:
    from typing import Any, Iterator

    from .typing import Connection, Cursor


class TransactionCursor:

    """Cursor context manager which starts a transaction and rolls back in case of error."""

    def __init__(self, conn):
        # type: (Connection, ) -> None

        self.cursor = conn.cursor()

    def __enter__(self):
        # type: () -> Cursor

        self.cursor.execute("BEGIN TRANSACTION")
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Any, Any, Any) -> None

        if exc_type:
            self.cursor.execute("ROLLBACK TRANSACTION")
        else:
            self.cursor.execute("COMMIT TRANSACTION")
        self.cursor.close()


class CursorContext:

    """Cursor context manager which creates a new cursor and closes it when it leaves the context."""

    def __init__(self, conn):
        # type: (Connection, ) -> None

        self.cursor = conn.cursor()

    def __enter__(self):
        # type: () -> Cursor

        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Any, Any, Any) -> None

        self.cursor.close()


def upsert(cursor, primary, values, table):
    # type: (Cursor, dict, dict, str) -> bool

    """Inserts `table` fields specified by `primary` and `values` keys,
    with the corresponding values.
    If all the values specified by `primary` already exist,
    they are updated instead.

    `table`, `primary.keys()` and `values.keys()` are not escaped.
    `primary.values()` and `values.values()` are escaped.
    """

    # use INSERT ... ON DUPLICATE KEY UPDATE instead?

    if not primary:
        raise ValueError("Empty primary mapping would result in an empty WHERE condition which would affect all rows")

    set_str = ",".join(f"{k}=?" for k in values.keys())
    where_str = " AND ".join(f"{k}=?" for k in primary.keys())

    cursor.execute(f"UPDATE {table} SET {set_str} WHERE {where_str}", chain(values.values(), primary.values()))  # nosec

    if cursor.rowcount == 0:
        into_str = ",".join(chain(primary.keys(), values.keys()))
        values_str = ",".join(repeat("?", len(primary) + len(values)))
        cursor.execute(
            f"INSERT INTO {table} ({into_str}) VALUES ({values_str})", chain(primary.values(), values.values())  # nosec
        )
        return True

    return False


def fetchone(cursor):
    # type: (Cursor, ) -> Any

    """Fetch results from `cursor` and assure only one result was returned."""

    rows = cursor.fetchall()
    if len(rows) == 0:
        raise NoResult("No result found")
    elif len(rows) == 1:
        return rows[0]
    else:
        raise InconsistentState("More than one result found")


def iterfetch(cursor, batchsize=1000):
    # type: (Cursor, int) -> Iterator[Any]

    """Iterate all results from `cursor`."""

    while True:
        results = cursor.fetchmany(batchsize)
        if not results:
            break
        yield from results
