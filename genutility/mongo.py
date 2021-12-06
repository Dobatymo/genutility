from __future__ import generator_stop

from typing import TYPE_CHECKING

from .exceptions import InconsistentState, NoResult

if TYPE_CHECKING:
    from pymongo.collection import Collection


def findone(db, query):
    # type: (Collection, dict) -> dict

    docs = list(db.find(query))

    if len(docs) == 0:
        raise NoResult("No result found")
    elif len(docs) == 1:
        return docs[0]
    else:
        raise InconsistentState("More than one result found")
