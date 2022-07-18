from __future__ import generator_stop

from operator import itemgetter
from typing import Any, Dict

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


def query_wikidata(query: str) -> Dict[str, Any]:
    url = "https://query.wikidata.org/sparql"
    r = requests.get(url, params={"format": "json", "query": query})
    r.raise_for_status()
    return r.json()
