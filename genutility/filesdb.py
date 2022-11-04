from __future__ import generator_stop

import logging
import os.path
import sqlite3
from itertools import chain, repeat
from os import fspath
from typing import Any, Callable, Collection, Dict, FrozenSet, Iterable, Iterator, List, Optional, Tuple, TypeVar

from tls_property import tls_property

from .exceptions import NoResult
from .filesystem import EntryType, normalize_seps
from .sql import fetchone, iterfetch
from .sqlite import quote_identifier

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GenericFileDb:

    order_col = "_order"

    def __init__(self, dbpath: str, table: str, debug: bool = True, allow_add: bool = True) -> None:

        self.table = quote_identifier(table)
        self._primary = self.primary()
        self._auto = self.auto()
        self._mandatory = self.mandatory()
        self._derived = self.derived()

        self.dbpath = dbpath
        self.setup()

        if logger.isEnabledFor(logging.DEBUG):
            logger.info("SQLite tracing enabled")
            self.connection.set_trace_callback(self.trace)

        # verify columns
        sql = f"SELECT c.name FROM pragma_table_info({self.table}) c"  # nosec
        self.cursor.execute(sql)
        file_cols = {name for name, in self.cursor.fetchall()}
        db_cols = {n: t for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived)}

        if self.order_col in db_cols:
            raise ValueError(f"`{self.order_col}` is a reserved column name")

        missing_cols = db_cols.keys() - file_cols
        if missing_cols:
            if allow_add:
                logger.info("Adding columns to database: %s", ", ".join(missing_cols))
                for name in missing_cols:
                    sql = f"ALTER TABLE {self.table} ADD {name} {db_cols[name]}"
                    self.cursor.execute(sql)
                self.commit()
            else:
                raise ValueError(f"Database is missing columns: {', '.join(missing_cols)}")

    @tls_property
    def connection(self):
        return sqlite3.connect(self.dbpath, check_same_thread=False)

    @tls_property
    def cursor(self):
        return self.connection.cursor()

    def trace(self, query: str) -> None:
        logger.debug("SQL trace: %s", query)

    @classmethod
    def latest_order_by(cls) -> str:
        return "entry_date DESC"

    @classmethod
    def primary(cls) -> List[Tuple[str, str, str]]:
        """Never explicitly specified.
        Not needed if there is a PRIMARY KEY in one of the other fields.
        """

        raise NotImplementedError

    @classmethod
    def auto(cls) -> List[Tuple[str, str, str]]:
        """Explicitly specified value.
        Can never be a ? placeholder, but must be a SQL value like `datetime('now')`.
        """

        raise NotImplementedError

    @classmethod
    def mandatory(cls) -> List[Tuple[str, str, str]]:
        """Mandatory fields used to retrieve rows.
        Used for all search queries.
        """

        raise NotImplementedError

    @classmethod
    def derived(cls) -> List[Tuple[str, str, str]]:
        """Optional fields used to retrieve rows.
        Used for search queries when given.
        """

        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __len__(self) -> int:
        sql = f"SELECT count(*) FROM {self.table}"  # nosec
        self.cursor.execute(sql)
        (result,) = fetchone(self.cursor)
        return result

    def close(self) -> None:

        """Only closes connections and cursors opened in the current thread"""

        self.cursor.close()
        self.connection.close()

    def setup(self) -> None:

        fields = ", ".join(f"{n} {t}" for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived))

        # unique = "UNIQUE({})".format(n for n, t, v in chain(self._mandatory, self._derived))
        # add to sql below?
        sql = f"CREATE TABLE IF NOT EXISTS {self.table} ({fields})"
        self.cursor.execute(sql)
        self.commit()

    def normalize_path(self, path):
        raise NotImplementedError

    def commit(self) -> None:

        self.connection.commit()

    def _args(
        self,
        path: str,
        filesize: int,
        mod_date: int,
        derived: Dict[str, Any],
        ignore_null: bool = True,
    ) -> tuple:

        if ignore_null:
            return tuple(
                chain(
                    (self.normalize_path(path), filesize, mod_date),
                    (derived[n] for n, t, v in self._derived if n in derived),
                )
            )
        else:
            return tuple(
                chain((self.normalize_path(path), filesize, mod_date), (derived.get(n) for n, t, v in self._derived))
            )

    def _args_many(
        self,
        mandatory: Iterable[Tuple[str, int, int]],
        derived: Optional[Iterable[Dict[str, Any]]] = None,
        ignore_null: bool = True,
    ) -> Iterator[tuple]:
        derived = derived or repeat({})
        for (path, filesize, mod_date), _derived in zip(mandatory, derived):
            yield self._args(path, filesize, mod_date, _derived, ignore_null)

    def iter(self, only: FrozenSet[str] = frozenset(), no: FrozenSet[str] = frozenset()) -> Iterator[tuple]:

        if only and no:
            raise ValueError("Only `only` or `no` can be specified")

        if only:
            fields = ", ".join(
                n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n in only
            )
        else:
            fields = ", ".join(
                n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n not in no
            )

        sql = f"SELECT {fields} FROM {self.table}"  # nosec
        self.cursor.execute(sql)
        return iterfetch(self.cursor)

    def _filtered_derived(self, derived: Collection[str], ignore_null: bool):

        if ignore_null:
            return ((n, t, v) for n, t, v in self._derived if n in derived)
        else:
            return self._derived

    def _get_fields(self, only: FrozenSet[str], no: FrozenSet[str]) -> List[str]:
        if only and no:
            raise ValueError("Only `only` or `no` can be specified")

        if only:
            fields = [n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n in only]
        else:
            fields = [n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n not in no]

        if not fields:
            raise ValueError("No output fields selected")

        return fields

    def get_latest(
        self,
        path: str,
        filesize: int,
        mod_date: int,
        derived: Optional[Dict[str, Any]] = None,
        ignore_null: bool = True,
        only: FrozenSet[str] = frozenset(),
        no: FrozenSet[str] = frozenset(),
    ) -> tuple:

        """Retrieve latest row based on mandatory and derived information.

        If `ignore_null=True` (default), values which are not provided in `derived`
        are ignored for the search.
        If it's `False`, values not provided in `derived` are assumed to be NULL
        and the row is only matches if the values in the database are NULL as well.

        The `only` argument can be used to include only these fields fields in the output.
        The `no` argument can be used to omit fields from the output.
        Only one of them can be specified.
        """

        derived = derived or {}

        fields = ", ".join(self._get_fields(only, no))
        _derived = self._filtered_derived(derived, ignore_null)
        conditions = " AND ".join(f"{n} IS ?" for n, t, v in chain(self._mandatory, _derived))
        order_by = self.latest_order_by()

        sql = f"SELECT {fields} FROM {self.table} WHERE {conditions} ORDER BY {order_by} LIMIT 1"  # nosec
        args = self._args(path, filesize, mod_date, derived, ignore_null)

        self.cursor.execute(sql, args)

        return fetchone(self.cursor)

    def get_latest_many(
        self,
        mandatory: Iterable[Tuple[str, int, int]],
        total: int,
        derived_names: Optional[Tuple[str, ...]] = None,
        derived: Optional[Iterable[Dict[str, Any]]] = None,
        ignore_null: bool = True,
        only: FrozenSet[str] = frozenset(),
        no: FrozenSet[str] = frozenset(),
    ) -> Iterator[tuple]:

        """`derived_names` must be equal to the keys of the `derived` dicts"""

        # This function creates a join table to match multiple values at once
        # and also allow carrying the input order over to the output.
        # Another implementation could use `WHERE (x1 AND y1) OR (x2 AND y2)`,
        # but this way doesn't easily support sorting.

        derived_names = derived_names or {}
        derived = derived or {}

        _derived = self._filtered_derived(derived_names, ignore_null)
        affected_fields = [n for n, t, v in chain(self._mandatory, _derived)]
        group_by = ", ".join(affected_fields)
        vars = len(affected_fields)
        values = ", ".join(f"({i}, {', '.join(repeat('?', vars))})" for i in range(total))
        select = ", ".join(f"t.{n}" for n in self._get_fields(only, no))
        join_on = " AND ".join(f"c.{n} = t.{n}" for n in affected_fields)
        join_group_by = ", ".join(f"t.{n}" for n in affected_fields)

        # fmt: off
        sql = (  # nosec
        f"""
            WITH conditions ({self.order_col}, {group_by}) AS (VALUES {values})  -- create table with order key and match values
            SELECT {select}
            FROM {self.table} t INNER JOIN conditions c ON {join_on}
            GROUP BY {join_group_by} HAVING entry_date = max(entry_date)  -- select only the latest entry from each group
            ORDER BY c.{self.order_col}  -- order rows according to input order
        """
        )
        # fmt: on
        args = tuple(chain.from_iterable(self._args_many(mandatory, derived)))

        self.cursor.execute(sql, args)

        return iterfetch(self.cursor)

    def get(self, path: EntryType, only: FrozenSet[str] = frozenset(), no: FrozenSet[str] = frozenset()) -> tuple:

        """Retrieves latest row based on mandatory information
        which is solely based on the `path`.
        Use `only`/`no` to include/exclude returned fields.
        """

        stats = path.stat()
        return self.get_latest(fspath(path), stats.st_size, stats.st_mtime_ns, ignore_null=True, only=only, no=no)

    def _filtered_values_str(self, derived, ignore_null: bool):
        return

    def _add_file(self, path: str, filesize: int, mod_date: int, derived: Dict[str, Any], replace: bool = True) -> None:

        """Adds a new entry to the database and doesn't check if file
        with the same mandatory fields already exists.
        However it will replace entries based on PRIMARY KEYs or UNIQUE indices.
        If `replace` is True the values previously existing in the existing replaced row but not given in `derived` will be overwritten with empty values.
        If `replace` is False, only the given values will be updated.
        """

        _derived = list(self._filtered_derived(derived, ignore_null=True))
        affected_fields = [n for n, t, v in chain(self._auto, self._mandatory, _derived)]
        fields = ", ".join(affected_fields)
        values = ", ".join(v for n, t, v in chain(self._auto, self._mandatory, _derived))

        if replace:
            sql = f"REPLACE INTO {self.table} ({fields}) VALUES ({values})"
        else:
            # fixme: this might keep the wrong derived information if the non-primary mandatory data like filesize or mod_date changed
            update_set = ", ".join(f"{n}=excluded.{n}" for n in affected_fields)
            sql = (
                f"INSERT INTO {self.table} ({fields}) VALUES ({values}) ON CONFLICT DO UPDATE SET {update_set}"  # nosec
            )

        args = self._args(path, filesize, mod_date, derived, ignore_null=True)

        assert self.cursor.execute(sql, args).rowcount == 1

    def _add_file_no_dup(
        self,
        path: str,
        filesize: int,
        mod_date: int,
        derived: Optional[Dict[str, Any]] = None,
        ignore_null: bool = True,
    ) -> bool:

        """Only adds a new entry to the db if the provided information
        does not exist in the db yet.
        """

        derived = derived or {}
        _derived = list(self._filtered_derived(derived, ignore_null))
        fields = ", ".join(n for n, t, v in chain(self._auto, self._mandatory, _derived))
        values = ", ".join(v for n, t, v in chain(self._auto, self._mandatory, _derived))
        conditions = " AND ".join(f"{n} IS ?" for n, t, v in chain(self._mandatory, _derived))

        sql = f"REPLACE INTO {self.table} ({fields}) SELECT {values} WHERE NOT EXISTS (SELECT 1 FROM {self.table} WHERE {conditions})"  # nosec
        args = self._args(path, filesize, mod_date, derived, ignore_null) * 2

        return self.cursor.execute(sql, args).rowcount == 1

        """ fixme: benchmark if this is really slower
        try:
            self.get_latest(path, filesize, mod_date, derived, ignore_null=ignore_null)
            return False

        except NoResult:
            self._add_file(path, filesize, mod_date, derived)
            return True
        """

    def add(
        self, path: EntryType, derived: Optional[Dict[str, Any]] = None, commit: bool = True, replace: bool = True
    ) -> None:

        """Adds a new entry to the database and doesn't check if file
        with the same mandatory fields already exists.
        However it will replace entries based on PRIMARY KEYs or UNIQUE indices
        """

        derived = derived or {}
        stats = path.stat()
        self._add_file(fspath(path), stats.st_size, stats.st_mtime_ns, derived, replace)
        if commit:
            self.commit()

    def add_file(self, path: str, filesize: int, mod_date: int, derived: Optional[Dict[str, Any]] = None) -> bool:

        """Only adds a new entry to the db if all the provided information doesn't match a row in the db yet."""

        result = self._add_file_no_dup(path, filesize, mod_date, derived)
        self.commit()
        return result

    def add_files(self, batch: Iterable[Tuple[str, int, int, Optional[Dict[str, Any]]]]) -> Iterator[bool]:

        """Adds multiple new entries to the db while ignoring already existing entries with the same information.
        Yields True for new entries, False otherwise.
        """

        for path, filesize, mod_date, derived in batch:
            yield self._add_file_no_dup(path, filesize, mod_date, derived)

        self.commit()

    def setdefault(self, path: EntryType, key: str, func: Callable[[], T]) -> T:
        try:
            (value,) = self.get(path, only={key})
            logger.debug("Found %s of %s in db: %s", key, path, value)
        except NoResult:
            value = func()
            self.add(path, derived={key: value})
            logger.debug("Added %s of %s to db: %s", key, path, value)

        return value


class FileDbHistory(GenericFileDb):
    @classmethod
    def primary(cls):
        return [
            ("file_id", "INTEGER NOT NULL PRIMARY KEY", "?"),
        ]

    @classmethod
    def auto(cls):
        return [
            ("entry_date", "DATETIME", "datetime('now')"),
        ]

    @classmethod
    def mandatory(cls):
        return [
            ("path", "VARCHAR(256)", "?"),
            ("filesize", "INTEGER", "?"),
            ("mod_date", "INTEGER", "?"),
        ]

    def normalize_path(self, path):
        drive, path = os.path.splitdrive(path)
        return normalize_seps(os.path.normpath(path))


class FileDbSimple(GenericFileDb):
    @classmethod
    def primary(cls):
        return []

    @classmethod
    def auto(cls):
        return [
            ("entry_date", "DATETIME", "datetime('now')"),
        ]

    @classmethod
    def mandatory(cls):
        return [
            ("path", "VARCHAR(256) NOT NULL PRIMARY KEY", "?"),
            ("filesize", "INTEGER", "?"),
            ("mod_date", "INTEGER", "?"),
        ]

    def normalize_path(self, path):
        return path
