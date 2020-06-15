from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from pandas import DataFrame, Series

from .func import identity

if TYPE_CHECKING:
	from typing import Any, Callable, Iterable, List, Optional, Tuple, TypeVar
	T = TypeVar("T")

def pandas_json(obj):
	# type: (Any, ) -> Any

	""" Can be used for the `json.dump` `default` argument
		to make some pandas objects JSON serializable.
	"""

	if isinstance(obj, DataFrame):
		return dict(obj)
	elif isinstance(obj, Series):
		return tuple(obj)

	raise TypeError("object of type {} cannot be JSON serialized: {}".format(type(obj), obj))

def strlist(sep):
	# type: (str, ) -> Callable[[str], List[str]]

	def inner(s):
		if s:
			return s.split(sep)
		else:
			return []

	return inner

def dataframe_to_dict(df, empty=False, cellfunc=None, dictcls=dict):
	# type: (DataFrame, bool, Optional[Callable], Callable[[Iterable[Tuple[str, Any]]], T]) -> T

	""" Turns dataframes into trees. Columns first, then rows
	"""

	if cellfunc is None:
		cellfunc = identity

	def cols(series):
		for rowname, rowdata in series.iteritems():
			value = cellfunc(rowdata)
			if value or empty:
				yield rowname, value

	def rows(df):
		for colname, coldata in df.iteritems():
			value = dictcls(cols(coldata))
			if value or empty:
				yield colname, value

	return dictcls(rows(df))
