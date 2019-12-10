from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewkeys, viewvalues
from itertools import chain, repeat

def upsert(cursor, primary, values, table):
	# type: (Cursor, dict, dict, str) -> bool

	# use INSERT ... ON DUPLICATE KEY UPDATE instead?

	set_str = ",".join("{}=?".format(k) for k in viewkeys(values))
	where_str = " AND ".join("{}=?".format(k) for k in viewkeys(primary))
	cursor.execute("UPDATE {} SET {} WHERE {}".format(table, set_str, where_str),  # nosec
		chain(viewvalues(values), viewvalues(primary))
	)

	if cursor.rowcount == 0:
		into_str = ",".join(chain(viewkeys(primary), viewkeys(values)))
		values_str = ",".join(repeat("?", len(primary) + len(values)))
		cursor.execute("INSERT INTO {} ({}) VALUES ({})".format(table, into_str, values_str),  # nosec
			chain(viewvalues(primary), viewvalues(values))
		)
		return True

	return False
