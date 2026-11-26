from unittest.mock import Mock, patch

import requests

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
            "https://query.wikidata.org/sparql", params={"format": "json", "query": q}, timeout=120.0, headers=None
        )
        response.raise_for_status.assert_called_once_with()
        result = df.businessLabel.tolist()
        truth = ["Advanced Accelerator Applications", "Altaba", "Asset Acceptance"]
        self.assertEqual(truth, result)

    def test_headers(self):
        headers = {"User-Agent": "GenutilityTest/1.0", "Accept": "application/sparql-results+json"}
        response = Mock()
        response.json.return_value = WIKIDATA_RESPONSE

        with patch("genutility.sparql.requests.get", return_value=response) as get:
            result = query_wikidata("ASK {}", 10.0, headers=headers)

        get.assert_called_once_with(
            "https://query.wikidata.org/sparql",
            params={"format": "json", "query": "ASK {}"},
            timeout=10.0,
            headers=headers,
        )
        self.assertIs(result, WIKIDATA_RESPONSE)

    def test_session(self):
        for headers, expected_agent in (
            (None, "SessionAgent/1.0"),
            ({"User-Agent": "QueryAgent/1.0"}, "QueryAgent/1.0"),
        ):
            with self.subTest(headers=headers), requests.Session() as session:
                session.headers.update({"User-Agent": "SessionAgent/1.0", "X-Test": "retained"})
                response = Mock()
                response.json.return_value = WIKIDATA_RESPONSE

                with patch.object(session, "send", return_value=response) as send:
                    result = query_wikidata("ASK {}", timeout=None, headers=headers, session=session)

                send.assert_called_once()
                prepared = send.call_args.args[0]
                self.assertEqual(prepared.headers["User-Agent"], expected_agent)
                self.assertEqual(prepared.headers["X-Test"], "retained")
                self.assertIsNone(send.call_args.kwargs["timeout"])
                self.assertIs(result, WIKIDATA_RESPONSE)
                response.raise_for_status.assert_called_once_with()

    def test_http_error(self):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("HTTP error")

        with patch("genutility.sparql.requests.get", return_value=response), self.assertRaises(requests.HTTPError):
            query_wikidata("ASK {}")

        response.json.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
