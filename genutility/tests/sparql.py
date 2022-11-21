from __future__ import generator_stop

from genutility.sparql import query_wikidata, wikidata_to_dataframe
from genutility.test import MyTestCase


class SparqlTest(MyTestCase):
    def test_pipeline(self):
        q = """
        SELECT ?businessLabel ?ticker WHERE {
          ?business wdt:P31 wd:Q6881511.
          ?business wdt:P414 wd:Q82059.
          ?business wdt:P249 ?ticker.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        } ORDER BY ?ticker LIMIT 5
        """
        df = wikidata_to_dataframe(query_wikidata(q))
        result = df.ticker.tolist()
        truth = ["TSLA"]
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
