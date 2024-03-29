from genutility.sparql import query_wikidata, wikidata_to_dataframe
from genutility.test import MyTestCase


class SparqlTest(MyTestCase):
    def test_pipeline(self):
        q = """
        SELECT ?businessLabel WHERE {
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
          ?business p:P414 ?exchange.
          ?exchange ps:P414 wd:Q82059;
            pq:P249 ?ticker.
        } ORDER BY (?ticker) LIMIT 3
        """
        df = wikidata_to_dataframe(query_wikidata(q))
        result = df.businessLabel.tolist()
        truth = ["Advanced Accelerator Applications", "Altaba", "Asset Acceptance"]
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
