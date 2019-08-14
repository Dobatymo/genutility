from __future__ import absolute_import, division, print_function, unicode_literals

import sqlite3

def sqlite_vacuum(db_path):
	# type: (str, ) -> None

	""" Vacuums a sqlite database. """

	with sqlite3.connect(db_path) as conn:
		conn.execute("VACUUM")
