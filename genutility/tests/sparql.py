from __future__ import generator_stop

from genutility.sparql import query_wikidata, wikidata_to_dataframe
from genutility.test import MyTestCase


class SparqlTest(MyTestCase):
    def test_pipeline(self):
        q = """
        SELECT ?businessLabel WHERE {
            ?business wdt:P31 wd:Q6881511.
            SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        } LIMIT 20
        """
        df = wikidata_to_dataframe(query_wikidata(q))
        result = set(df.businessLabel[:5])
        truth = {"GitHub", "Apple", "Boeing", "Intel", "Airbus"}
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
