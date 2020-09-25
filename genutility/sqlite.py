from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import logging
import sqlite3
from typing import TYPE_CHECKING

from .iter import batch, progress
from .signal import safe_for_loop

if TYPE_CHECKING:
	from sqlite3 import Cursor, Iterable

def quote_identifier(s, errors="strict"):
	# type: (str, str) -> str

	""" Escapes sqlite identifiers (like table or column names).
		Copied from: https://stackoverflow.com/a/6701665
	"""

	encodable = s.encode("utf-8", errors).decode("utf-8")
	nul_index = encodable.find("\x00")

	if nul_index >= 0:
		error = UnicodeEncodeError("NUL-terminated utf-8", encodable, nul_index, nul_index + 1, "NUL not allowed")
		error_handler = codecs.lookup_error(errors)
		replacement, _ = error_handler(error)
		encodable = encodable.replace("\x00", replacement)

	return "\"" + encodable.replace("\"", "\"\"") + "\""

def vacuum(db_path):
	# type: (str, ) -> None

	""" Vacuums a sqlite database. """

	with sqlite3.connect(db_path) as conn:
		conn.execute("VACUUM")

def batch_executer(cursor, query_str, it, batch_size=10000, exclusive=True):
	# type: (Cursor, str, Iterable[tuple], int, bool) -> int

	""" Execute `query_str` with parameters from `it` batch-wise with batches of size `batch_size`.
		If `exclusive` is True the database will be locked in exclusive mode.
	"""

	if exclusive:
		cursor.execute("PRAGMA locking_mode=EXCLUSIVE") # might speed things up

	entries = 0

	for queries_batch in batch(progress(it), batch_size):

		# need to cache batch data, because if the iterable is exhausted,
		# executemany raises `sqlite3.ProgrammingError`
		data = list(queries_batch) 
		if data:
			cursor.execute("BEGIN TRANSACTION")
			cursor.executemany(query_str, data)
			cursor.execute("COMMIT TRANSACTION")
			entries += len(data)

	return entries

def safe_batch_executer(cursor, query_str, it, batch_size=10000, exclusive=True):
	# type: (Cursor, str, Iterable[tuple], int, bool) -> None

	""" Execute `query_str` with parameters from `it` batch-wise with batches of size `batch_size`.
		If `exclusive` is True the database will be locked in exclusive mode.
		If an db integrity error occurs, the batch will be skipped and the transaction for
		this batch rolled back.
		If the iterable is advanced, the user can be sure its elements will be inserted into the
		database, even if a KeyboardInterrupt is received in-between.
	"""

	if exclusive:
		cursor.execute("PRAGMA locking_mode=EXCLUSIVE")  # might speed things up

	source = batch(progress(it), batch_size)

	def sqlexec(queries_batch):
		try:
			cursor.execute("BEGIN TRANSACTION")
			cursor.executemany(query_str, queries_batch)
			cursor.execute("COMMIT TRANSACTION")
		except sqlite3.IntegrityError:
			logging.info("Skipping batch")
			cursor.execute("ROLLBACK TRANSACTION")
		except sqlite3.OperationalError:
			raise

	try:
		safe_for_loop(source, sqlexec)
	except KeyboardInterrupt:
		logging.info("Batch execution safely interrupted")
