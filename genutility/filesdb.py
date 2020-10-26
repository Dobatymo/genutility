from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os.path
import sqlite3
from itertools import chain
from typing import TYPE_CHECKING

from tls_property import tls_property

from .compat.os import fspath
from .exceptions import NoResult
from .filesystem import normalize_seps
from .sql import fetchone, iterfetch
from .sqlite import quote_identifier

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from typing import Any, Dict, Iterable, Iterator, Optional, Set

	from .filesystem import EntryType

class GenericFileDb(object):

	def __init__(self, dbpath, table, debug=True):
		# type: (str, str, bool) -> None

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

	@tls_property
	def connection(self):
		return sqlite3.connect(self.dbpath, check_same_thread=False)

	@tls_property
	def cursor(self):
		return self.connection.cursor()

	def trace(self, query):
		logger.debug("SQL trace: %s", query)

	@classmethod
	def latest_order_by(cls):
		return "entry_date DESC"

	@classmethod
	def primary(cls):
		""" Never explicitly specified.
			Not needed if there is a PRIMARY KEY in one of the other fields.
		"""

		raise NotImplementedError

	@classmethod
	def auto(cls):
		""" Explicitly specified value.
			Can never be a ? placeholder, but must be a SQL value like `datetime('now')`.
		"""

		raise NotImplementedError

	@classmethod
	def mandatory(cls):
		""" Mandatory fields used to retrieve rows.
			Used for all search queries.
		"""

		raise NotImplementedError

	@classmethod
	def derived(cls):
		""" Optional fields used to retrieve rows.
			Used for search queries when given.
		"""

		raise NotImplementedError

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

	def close(self):
		# type: () -> None

		""" Only closes connections and cursors opened in the current thread
		"""

		self.cursor.close()
		self.connection.close()

	def setup(self):
		# type: () -> None

		fields = ", ".join("{} {}".format(n, t) for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived))

		# unique = "UNIQUE({})".format(n for n, t, v in chain(self._mandatory, self._derived))
		# add to sql below?
		sql = "CREATE TABLE IF NOT EXISTS {} ({})".format(self.table, fields)

		self.cursor.execute(sql)
		self.commit()

	def normalize_path(self, path):
		raise NotImplementedError

	def commit(self):
		# type: () -> None

		self.connection.commit()

	def _args(self, path, filesize, mod_date, derived=None, ignore_null=True):
		# type: (str, int, int, Optional[Dict[str, Any]], bool) -> tuple

		derived = derived or {}
		if ignore_null:
			return tuple(chain((self.normalize_path(path), filesize, mod_date), (derived[n] for n, t, v in self._derived if n in derived)))
		else:
			return tuple(chain((self.normalize_path(path), filesize, mod_date), (derived.get(n) for n, t, v in self._derived)))

	def iter(self, only=frozenset(), no=frozenset()):
		# type: (Set[str], Set[str]) -> Iterator[tuple]

		if only and no:
			raise ValueError("Only `only` or `no` can be specified")

		if only:
			fields = ", ".join(n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n in only)
		else:
			fields = ", ".join(n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n not in no)

		self.cursor.execute("SELECT {} FROM {}".format(fields, self.table))  # nosec
		return iterfetch(self.cursor)

	def get_latest(self, path, filesize, mod_date, derived=None, ignore_null=True, only=frozenset(), no=frozenset()):
		# type: (str, int, int, Optional[Dict[str, Any]], bool, Set[str], Set[str]) -> tuple

		""" Retrieve latest row based on mandatory and derived information.

			If `ignore_null=True` (default), values which are not provided in `derived`
			are ignored for the search.
			If it's `False`, values not provided in `derived` are assumed to be NULL
			and the row is only matches if the values in the database are NULL as well.

			The `only` argument can be used to include only these fields fields in the output.
			The `no` argument can be used to omit fields from the output.
			Only one of them can be specified.
		"""

		if only and no:
			raise ValueError("Only `only` or `no` can be specified")

		derived = derived or {}
		args = self._args(path, filesize, mod_date, derived, ignore_null)

		if ignore_null:
			_derived = ((n, t, v) for n, t, v in self._derived if n in derived)
		else:
			_derived = self._derived

		if only:
			fields = ", ".join(n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n in only)
		else:
			fields = ", ".join(n for n, t, v in chain(self._primary, self._auto, self._mandatory, self._derived) if n not in no)

		if not fields:
			raise ValueError("No output fields selected")

		conditions = " AND ".join("{} IS ?".format(n) for n, t, v in chain(self._mandatory, _derived))
		order_by = self.latest_order_by()
		sql = "SELECT {} FROM {} WHERE {} ORDER BY {} LIMIT 1".format(fields, self.table, conditions, order_by)  # nosec

		self.cursor.execute(sql, args)

		return fetchone(self.cursor)

	def get(self, path, only=frozenset(), no=frozenset()):
		# type: (EntryType, Set[str], Set[str]) -> tuple

		""" Retrieves latest row based on mandatory information
			which is solely based on the `path`.
			Use `only`/`no` to include/exclude returned fields.
		"""

		stats = path.stat()
		return self.get_latest(fspath(path), stats.st_size, stats.st_mtime_ns, ignore_null=True, only=only, no=no)

	def _add_file(self, path, filesize, mod_date, derived=None):
		# type: (str, int, int, Optional[Dict[str, Any]]) -> None

		""" Adds a new entry to the database and doesn't check if file
			with the same mandatory fields already exists.
			However it will replace entries based on PRIMARY KEYs or UNIQUE indices
		"""

		args = self._args(path, filesize, mod_date, derived, ignore_null=False)

		fields = ", ".join(n for n, t, v in chain(self._auto, self._mandatory, self._derived))
		values = ", ".join(v for n, t, v in chain(self._auto, self._mandatory, self._derived))
		sql = "REPLACE INTO {} ({}) VALUES ({})".format(self.table, fields, values)
		self.cursor.execute(sql, args)

	def _add_file_no_dup(self, path, filesize, mod_date, derived=None, ignore_null=True):
		# type: (str, int, int, Optional[Dict[str, Any]], bool) -> bool

		""" Only adds a new entry to the db if the provided information
			does not exist in the db yet.
		"""

		try:
			result = self.get_latest(path, filesize, mod_date, derived, ignore_null=ignore_null)
			return False

		except NoResult:
			self._add_file(path, filesize, mod_date, derived)
			return True

	def add(self, path, derived=None, commit=True):
		# type: (EntryType, Optional[Dict[str, Any]]) -> None

		stats = path.stat()
		self._add_file(fspath(path), stats.st_size, stats.st_mtime_ns, derived)
		if commit:
			self.commit()

	def add_file(self, path, filesize, mod_date, derived=None):
		# type: (str, int, int, Optional[Dict[str, Any]]) -> bool

		result = self._add_file_no_dup(path, filesize, mod_date, derived)
		self.commit()
		return result

	def add_files(self, batch):
		# type: (Iterable[str, int, int, Optional[Dict[str, Any]]], ) -> Iterator[bool]

		for path, filesize, mod_date, derived in batch:
			yield self._add_file_no_dup(path, filesize, mod_date, derived)

		self.commit()

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
