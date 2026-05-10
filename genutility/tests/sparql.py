from unittest.mock import Mock, patch

from genutility.sparql import query_wikidata, wikidata_to_dataframe
from genutility.test import MyTestCase

WIKIDATA_RESPONSE = {
    "head": {"vars": ["businessLabel"]},
    "results": {
        "bindings": [
            {
                "businessLabel": {
                    "xml:lang": "en",
                    "type": "literal",
                    "value": "Advanced Accelerator Applications",
                }
            },
            {
                "businessLabel": {
                    "xml:lang": "en",
                    "type": "literal",
                    "value": "Altaba",
                }
            },
            {
                "businessLabel": {
                    "xml:lang": "en",
                    "type": "literal",
                    "value": "Asset Acceptance",
                }
            },
        ]
    },
}


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
        response = Mock()
        response.json.return_value = WIKIDATA_RESPONSE

        with patch("genutility.sparql.requests.get", return_value=response) as get:
            df = wikidata_to_dataframe(query_wikidata(q))

        get.assert_called_once_with(
            "https://query.wikidata.org/sparql", params={"format": "json", "query": q}, timeout=120.0
        )
        response.raise_for_status.assert_called_once_with()
        result = df.businessLabel.tolist()
        truth = ["Advanced Accelerator Applications", "Altaba", "Asset Acceptance"]
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
