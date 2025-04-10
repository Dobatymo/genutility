import logging
import os
import os.path
import sqlite3
import warnings
from collections import UserDict
from functools import lru_cache
from itertools import chain, repeat
from pathlib import Path
from typing import Any, Callable, Collection, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, TypeVar, Union

from tls_property import tls_property
from typing_extensions import Self

from .exceptions import NoResult
from .filesystem import EntryType, normalize_seps
from .sql import fetchone, iterfetch
from .sqlite import quote_identifier
from .typing import HashableContainer

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Keys(UserDict):
    def __hash__(self):
        return hash(tuple(self))


class GenericDb:
    order_col = "_order"

    def __init__(self, dbpath: Union[str, os.PathLike], table: str, debug: bool = True, allow_add: bool = True) -> None:
        if sqlite3.sqlite_version_info < (3, 35, 0):
            warnings.warn(
                f"SQLite version 3.35.0 or higher required for some features (current version {sqlite3.sqlite_version}). ",
                stacklevel=2,
            )

        self.table = quote_identifier(table)
        self._primary = self.primary()
        self._auto = self.auto()
        self._mandatory = self.mandatory()
        self._derived = self.derived()

        self.dbpath = dbpath
        self.setup()

        if logger.isEnabledFor(logging.DEBUG):
            logger.info("SQLite tracing enabled")
            sqlite3.enable_callback_tracebacks(True)
            self.connection.set_trace_callback(self.trace)

        # verify columns
        sql = f"SELECT c.name FROM pragma_table_info({self.table}) c"  # nosec
        self.cursor.execute(sql)
        file_cols = {name for (name,) in self.cursor.fetchall()}
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

        self._get_latest_sql = lru_cache(maxsize=128)(self._get_latest_sql)  # type: ignore[assignment,method-assign]

    @tls_property
    def connection(self):
        if os.fspath(self.dbpath) != ":memory:" and not Path(self.dbpath).parent.is_dir():
            raise FileNotFoundError(self.dbpath)
        return sqlite3.connect(self.dbpath, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)

    @tls_property
    def cursor(self):
        return self.connection.cursor()

    def trace(self, query: str) -> None:
        logger.debug("SQL trace: %s", query)

    @classmethod
    def latest_order_by(cls) -> Tuple[str, str, str]:
        raise NotImplementedError

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

        return []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def __len__(self) -> int:
        sql = f"SELECT count(*) FROM {self.table}"  # nosec
        self.cursor.execute(sql)
        (result,) = fetchone(self.cursor)
        return result

    def __bool__(self) -> bool:
        sql = f"SELECT EXISTS (SELECT 1 FROM {self.table})"  # nosec
        self.cursor.execute(sql)
        (result,) = fetchone(self.cursor)
        return result == 1

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

    def normalize_mandatory(self, mandatory: Sequence) -> Sequence:
        return mandatory

    def commit(self) -> None:
        self.connection.commit()

    def _args(
        self,
        mandatory: Sequence[Any],
        derived: Dict[str, Any],
        ignore_null: bool = True,
    ) -> tuple:
        if ignore_null:
            return tuple(
                chain(
                    self.normalize_mandatory(mandatory),
                    (derived[n] for n, t, v in self._derived if n in derived),
                )
            )
        else:
            return tuple(chain(self.normalize_mandatory(mandatory), (derived.get(n) for n, t, v in self._derived)))

    def _args_many(
        self,
        mandatory: Iterable[Sequence[Any]],
        derived: Optional[Iterable[Dict[str, Any]]] = None,
        ignore_null: bool = True,
    ) -> Iterator[tuple]:
        derived = derived or repeat({})
        for _mandatory, _derived in zip(mandatory, derived):
            yield self._args(_mandatory, _derived, ignore_null)

    def iter(
        self, only: HashableContainer[str] = frozenset(), no: HashableContainer[str] = frozenset()
    ) -> Iterator[tuple]:
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

    def _filtered_derived(self, derived: Collection[str], select: str) -> Iterable[Tuple[str, str, str]]:
        if select == "null":
            return ((n, t, v) for n, t, v in self._derived if n not in derived)
        elif select == "not-null":
            return ((n, t, v) for n, t, v in self._derived if n in derived)
        elif select == "all":
            return self._derived
        else:
            raise ValueError("select must be one of: null, not-null, all")

    def _get_fields(self, only: HashableContainer[str], no: HashableContainer[str]) -> List[str]:
        if only and no:
            raise ValueError("Only `only` or `no` can be specified")

        if only:
            fields = [n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n in only]
        else:
            fields = [n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n not in no]

        if not fields:
            raise ValueError("No output fields selected")

        return fields

    def _get_latest_sql(
        self, derived_keys: Collection[str], ignore_null: bool, only: HashableContainer[str], no: HashableContainer[str]
    ) -> str:
        fields = ", ".join(self._get_fields(only, no))
        _derived = self._filtered_derived(derived_keys, "not-null" if ignore_null else "all")
        conditions = " AND ".join(f"{n} IS ?" for n, t, v in chain(self._mandatory, _derived))
        latest_col, latest_dir, latest_agg = self.latest_order_by()
        sql = (
            f"SELECT {fields} FROM {self.table} WHERE {conditions} ORDER BY {latest_col} {latest_dir} LIMIT 1"  # nosec
        )
        return sql

    def _get_latest(
        self,
        mandatory: Sequence[Any],
        derived: Optional[Dict[str, Any]] = None,
        ignore_null: bool = True,
        only: HashableContainer[str] = frozenset(),
        no: HashableContainer[str] = frozenset(),
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
        sql = self._get_latest_sql(Keys(derived), ignore_null, only, no)
        args = self._args(mandatory, derived, ignore_null)
        self.cursor.execute(sql, args)
        return fetchone(self.cursor)

    def get_latest_many(
        self,
        mandatory: Iterable[Sequence[Any]],
        total: int,
        derived_names: Optional[Tuple[str, ...]] = None,
        derived: Optional[Iterable[Dict[str, Any]]] = None,
        ignore_null: bool = True,
        only: HashableContainer[str] = frozenset(),
        no: HashableContainer[str] = frozenset(),
    ) -> Iterator[tuple]:
        """Retrieve multiple latest rows based on mandatory and derived information.
        `derived_names` must be equal to the keys of the `derived` dicts.

        See `_get_latest` for more details.
        """

        # This function creates a join table to match multiple values at once
        # and also allow carrying the input order over to the output.
        # Another implementation could use `WHERE (x1 AND y1) OR (x2 AND y2)`,
        # but this way doesn't easily support sorting.

        derived_names = derived_names or ()
        derived = derived or {}

        _derived = self._filtered_derived(derived_names, "not-null" if ignore_null else "all")
        affected_fields = [n for n, t, v in chain(self._mandatory, _derived)]
        group_by = ", ".join(affected_fields)
        vars = len(affected_fields)
        values = ", ".join(f"({i}, {', '.join(repeat('?', vars))})" for i in range(total))
        select = ", ".join(f"t.{n}" for n in self._get_fields(only, no))
        join_on = " AND ".join(f"c.{n} = t.{n}" for n in affected_fields)
        join_group_by = ", ".join(f"t.{n}" for n in affected_fields)

        latest_col, latest_dir, latest_agg = self.latest_order_by()
        sql = f"""
            WITH conditions ({self.order_col}, {group_by}) AS (VALUES {values})  -- create table with order key and match values
            SELECT {select}
            FROM {self.table} t INNER JOIN conditions c ON {join_on}
            GROUP BY {join_group_by} HAVING {latest_col} = {latest_agg}({latest_col})  -- select only the latest entry from each group
            ORDER BY c.{self.order_col}  -- order rows according to input order
        """  # nosec

        args = tuple(chain.from_iterable(self._args_many(mandatory, derived, ignore_null)))

        self.cursor.execute(sql, args)

        return iterfetch(self.cursor)

    def _filtered_values_str(self, derived, ignore_null: bool):
        return

    def _add_file_query(self, derived_names: Optional[Tuple[str, ...]] = None, replace: bool = True) -> str:
        _derived = list(self._filtered_derived(derived_names, "not-null"))
        affected_fields = [n for n, t, v in chain(self._auto, self._mandatory, _derived)]
        fields = ", ".join(affected_fields)
        values = ", ".join(v for n, t, v in chain(self._auto, self._mandatory, _derived))

        if replace:
            sql = f"REPLACE INTO {self.table} ({fields}) VALUES ({values})"
        else:
            condition = " AND ".join(f"{n} IS excluded.{n}" for n, t, v in self._mandatory)
            set_affected = (f"{n}=excluded.{n}" for n in affected_fields)
            set_unaffected = (
                f"{n}=CASE WHEN {condition} THEN {n} ELSE NULL END"
                for n, t, v in self._filtered_derived(derived_names, "null")
            )
            update_set = ", ".join(chain(set_affected, set_unaffected))
            sql = (
                f"INSERT INTO {self.table} ({fields}) VALUES ({values}) ON CONFLICT DO UPDATE SET {update_set}"  # nosec
            )

        return sql

    def _add_file(self, mandatory: Sequence[Any], derived: Dict[str, Any], replace: bool = True) -> None:
        """Adds a new entry to the database and doesn't check if file
        with the same mandatory fields already exists.
        It will replace or update entries based on matching PRIMARY KEY or UNIQUE field, or else insert them.
        If `replace` is True the values previously existing in the existing replaced row but not given in `derived`
        will be overwritten with empty values.
        If `replace` is False, the given derived values will be updated if all mandatory fields match,
        and not given ones will keep their original values. If not all of the mandatory fields match,
        not given derived values will be reset to zero.  This makes sure out-dated values are removed.
        """

        sql = self._add_file_query(derived, replace)
        args = self._args(mandatory, derived, ignore_null=True)

        assert self.cursor.execute(sql, args).rowcount == 1

    def _add_file_many(
        self,
        mandatory: Iterable[Sequence[Any]],
        derived_names: Optional[Tuple[str, ...]] = None,
        derived: Optional[Iterable[Dict[str, Any]]] = None,
        replace: bool = True,
    ) -> None:
        """Replace or upsert multiple files.
        `derived_names` must be equal to the keys of the `derived` dicts.

        See `_add_file` for more details.
        """

        sql = self._add_file_query(derived_names, replace)
        args = self._args_many(mandatory, derived, ignore_null=True)
        self.cursor.executemany(sql, args)

    def _add_file_no_dup(
        self,
        mandatory: Sequence[Any],
        derived: Optional[Dict[str, Any]] = None,
        ignore_null: bool = True,
    ) -> bool:
        """Only adds a new entry to the db if the provided information
        does not exist in the db yet.
        """

        derived = derived or {}
        _derived = list(self._filtered_derived(derived, "not-null" if ignore_null else "all"))
        fields = ", ".join(n for n, t, v in chain(self._auto, self._mandatory, _derived))
        values = ", ".join(v for n, t, v in chain(self._auto, self._mandatory, _derived))
        conditions = " AND ".join(f"{n} IS ?" for n, t, v in chain(self._mandatory, _derived))

        sql = f"REPLACE INTO {self.table} ({fields}) SELECT {values} WHERE NOT EXISTS (SELECT 1 FROM {self.table} WHERE {conditions})"  # nosec
        args = self._args(mandatory, derived, ignore_null) * 2

        return self.cursor.execute(sql, args).rowcount == 1

        """ fixme: benchmark if this is really slower
        try:
            self._get_latest(mandatory, derived, ignore_null=ignore_null)
            return False

        except NoResult:
            self._add_file(mandatory, derived)
            return True
        """


class GenericFileDb(GenericDb):
    @classmethod
    def latest_order_by(cls) -> Tuple[str, str, str]:
        return ("entry_date", "DESC", "max")

    def get_latest(
        self,
        path: str,
        filesize: int,
        mod_date: int,
        derived: Optional[Dict[str, Any]] = None,
        ignore_null: bool = True,
        only: HashableContainer[str] = frozenset(),
        no: HashableContainer[str] = frozenset(),
    ) -> tuple:
        mandatory = (path, filesize, mod_date)
        return self._get_latest(mandatory, derived, ignore_null, only, no)

    def get(
        self, path: EntryType, only: HashableContainer[str] = frozenset(), no: HashableContainer[str] = frozenset()
    ) -> tuple:
        """Retrieves latest row based on mandatory information
        which is solely based on the `path`.
        Use `only`/`no` to include/exclude returned fields.
        """

        stats = path.stat()
        return self.get_latest(os.fspath(path), stats.st_size, stats.st_mtime_ns, ignore_null=True, only=only, no=no)

    def add(
        self, path: EntryType, derived: Optional[Dict[str, Any]] = None, commit: bool = True, replace: bool = True
    ) -> None:
        """Adds a new entry to the database and doesn't check if file
        with the same mandatory fields already exists.
        However it will replace entries based on PRIMARY KEYs or UNIQUE indices
        """

        derived = derived or {}
        stats = path.stat()
        mandatory = (os.fspath(path), stats.st_size, stats.st_mtime_ns)
        self._add_file(mandatory, derived, replace)
        if commit:
            self.commit()

    def add_file(self, path: str, filesize: int, mod_date: int, derived: Optional[Dict[str, Any]] = None) -> bool:
        """Only adds a new entry to the db if all the provided information doesn't match a row in the db yet."""

        mandatory = (path, filesize, mod_date)
        result = self._add_file_no_dup(mandatory, derived)
        self.commit()
        return result

    def add_files(self, batch: Iterable[Tuple[str, int, int, Optional[Dict[str, Any]]]]) -> Iterator[bool]:
        """Adds multiple new entries to the db while ignoring already existing entries with the same information.
        Yields True for new entries, False otherwise.
        """

        for path, filesize, mod_date, derived in batch:
            mandatory = (path, filesize, mod_date)
            yield self._add_file_no_dup(mandatory, derived)

        self.commit()

    def setdefault(self, path: EntryType, key: str, func: Callable[[], T]) -> T:
        try:
            (value,) = self.get(path, only=frozenset((key,)))
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

    def normalize_mandatory(self, mandatory: Sequence) -> Sequence:
        path, filesize, mod_date = mandatory
        drive, path = os.path.splitdrive(mandatory[0])
        path = normalize_seps(os.path.normpath(path))
        return path, filesize, mod_date


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


def is_signed_int_64(num: int) -> bool:
    return -(2**63) <= num <= 2**63 - 1


def unsigned_to_signed_int_64(num: int) -> int:
    return num - 2**63


def signed_to_unsigned_int_64(num: int) -> int:
    return num + 2**63


class Uint64:
    __slots__ = ("value",)

    def __init__(self, value: int) -> None:
        self.value = value

    def to_bytes(self):
        return self.value.to_bytes(length=8, byteorder="big", signed=False)


def uint64_to_bytes(uint64: Uint64) -> bytes:
    return uint64.to_bytes()


def uint64_from_bytes(blob: bytes) -> int:
    return int.from_bytes(blob, byteorder="big", signed=False)


class FileDbWithId(GenericFileDb):
    def __init__(self, dbpath: Union[str, os.PathLike], table: str, debug: bool = True, allow_add: bool = True) -> None:
        GenericFileDb.__init__(self, dbpath, table, debug, allow_add)
        sqlite3.register_adapter(Uint64, uint64_to_bytes)
        sqlite3.register_converter("uint64", uint64_from_bytes)

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
            ("file_id", "uint64", "?"),
            ("device_id", "uint64", "?"),
            ("filesize", "INTEGER", "?"),
            ("mod_date", "INTEGER", "?"),
        ]

    def get(
        self, path: Path, only: HashableContainer[str] = frozenset(), no: HashableContainer[str] = frozenset()
    ) -> tuple:
        """Retrieves latest row based on mandatory information
        which is solely based on the `path`.
        Use `only`/`no` to include/exclude returned fields.
        """

        stats = path.stat()
        assert stats.st_ino != 0 and stats.st_dev != 0
        device = Uint64(stats.st_dev).to_bytes()
        inode = Uint64(stats.st_ino).to_bytes()
        mandatory = (os.fspath(path), inode, device, stats.st_size, stats.st_mtime_ns)
        return self._get_latest(mandatory, ignore_null=True, only=only, no=no)

    def add(
        self, path: Path, derived: Optional[Dict[str, Any]] = None, commit: bool = True, replace: bool = True
    ) -> None:
        """Adds a new entry to the database and doesn't check if file
        with the same mandatory fields already exists.
        However it will replace entries based on PRIMARY KEYs or UNIQUE indices
        """

        derived = derived or {}
        stats = path.stat()
        assert stats.st_ino != 0 and stats.st_dev != 0, stats

        # On windows st_dev and st_ino is unsigned 64 bit int, but sqlite only supports signed 64 bit ints.
        # I don't know about linux
        device = Uint64(stats.st_dev)
        inode = Uint64(stats.st_ino)

        mandatory = (os.fspath(path), inode, device, stats.st_size, stats.st_mtime_ns)
        self._add_file(mandatory, derived, replace)
        if commit:
            self.commit()
