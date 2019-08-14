from __future__ import absolute_import, division, print_function, unicode_literals

from .exceptions import NoResult, InconsistentState

def findone(db, query):
	docs = list(db.find(query))

	if len(docs) == 0:
		raise NoResult("No result found")
	elif len(docs) == 1:
		return docs[0]
	else:
		raise InconsistentState("More than one result found")
