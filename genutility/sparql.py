from operator import itemgetter
from typing import Any, Dict, Mapping, Optional

import pandas as pd
import requests

from .dict import mapmap


def wikidata_to_dataframe(result: Dict[str, Any]) -> pd.DataFrame:
    cols = result["head"]["vars"]

    getval = itemgetter("value")

    def gen():
        for row in result["results"]["bindings"]:
            yield tuple(map(getval, mapmap(row, cols)))

    return pd.DataFrame.from_records(gen(), columns=cols)


def query_wikidata(
    query: str,
    timeout: Optional[float] = 120.0,
    *,
    headers: Optional[Mapping[str, str]] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Query Wikidata with optional request headers and a caller-owned session.

    Headers can set a descriptive User-Agent or override session defaults.
    The caller remains responsible for closing a supplied session.
    """
    url = "https://query.wikidata.org/sparql"
    client = requests if session is None else session
    r = client.get(url, params={"format": "json", "query": query}, timeout=timeout, headers=headers)
    r.raise_for_status()
    return r.json()
