from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from .func import identity

if TYPE_CHECKING:
	from typing import Callable, Optional, List, TypeVar
	from pandas import DataFrame
	T = TypeVar("T")

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
