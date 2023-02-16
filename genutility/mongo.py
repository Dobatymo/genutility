from pymongo.collection import Collection

from .exceptions import InconsistentState, NoResult


def findone(db: Collection, query: dict) -> dict:
    docs = list(db.find(query))

    if len(docs) == 0:
        raise NoResult("No result found")
    elif len(docs) == 1:
        return docs[0]
    else:
        raise InconsistentState("More than one result found")
