"""Regression checks for ingestion, API contracts, filters and dashboard delivery."""

import csv
import tempfile
import unittest
from urllib.error import URLError
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ingestion import csv_profile, iter_csv_rows
from api_clients.common import fetch_bytes
from fetch_weather_history import valid_cache
from main import app


class IngestionTests(unittest.TestCase):
    def test_csv_profile_handles_thai_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_text("ชื่อ,ค่า\nอุทยาน,10\n", encoding="utf-8")
            rows = list(iter_csv_rows(path))
            profile = csv_profile(path)
            self.assertEqual(rows[0]["ชื่อ"], "อุทยาน")
            self.assertEqual(profile["row_count"], 1)

    def test_csv_profile_reports_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.csv"
            path.write_text("name,value\n", encoding="utf-8")
            profile = csv_profile(path)
            self.assertEqual(profile["row_count"], 0)
            self.assertEqual(profile["columns"], [])

    def test_weather_cache_rejects_malformed_response(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather.json"
            path.write_text('{"unexpected": true}', encoding="utf-8")
            self.assertFalse(valid_cache(path))

    @patch("api_clients.common.time.sleep", return_value=None)
    @patch("api_clients.common.urlopen", side_effect=URLError("timeout"))
    def test_http_retry_raises_clear_error(self, _urlopen, _sleep):
        with self.assertRaisesRegex(RuntimeError, "Unable to fetch"):
            fetch_bytes("https://example.invalid", retries=2)
        self.assertEqual(_urlopen.call_count, 2)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_core_endpoints(self):
        for path in ("/health", "/api/summary", "/api/monthly-visitors", "/api/park-visitors", "/api/environment"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_filters_change_result(self):
        all_data = self.client.get("/api/summary").json()
        year_data = self.client.get("/api/summary?year=2016").json()
        self.assertGreater(all_data["total_visitors"], year_data["total_visitors"])
        self.assertEqual(self.client.get("/api/summary?month=13").status_code, 422)

    def test_dashboard_is_served(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Nature Data Lab", response.text)
        self.assertIn("Compare Parks", response.text)

    def test_meta_compare_and_seasonality_contracts(self):
        meta = self.client.get("/api/meta").json()
        self.assertEqual(len(meta["parks"]), 11)
        self.assertGreater(meta["coverage"]["weather_rows"], 0)
        response = self.client.get("/api/compare?park_a=doi_inthanon&park_b=doi_suthep_pui&start_year=2016&end_year=2020")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("insights", payload)
        self.assertEqual(len(payload["park_a"]["seasonality"]), 12)
        summary = self.client.get("/api/summary?park=doi_inthanon").json()
        all_years = self.client.get("/api/compare?park_a=doi_inthanon&park_b=doi_suthep_pui&start_year=2015&end_year=2025").json()
        self.assertEqual(summary["total_visitors"], all_years["park_a"]["total_visitors"])

    def test_compare_validation_and_export(self):
        self.assertEqual(self.client.get("/api/compare?park_a=doi_inthanon&park_b=doi_inthanon").status_code, 422)
        self.assertEqual(self.client.get("/api/compare?park_a=unknown&park_b=doi_inthanon").status_code, 404)
        self.assertEqual(self.client.get("/api/compare?park_a=doi_inthanon&park_b=doi_suthep_pui&start_year=2025&end_year=2015").status_code, 422)
        export = self.client.get("/api/export.csv?park=doi_inthanon")
        self.assertEqual(export.status_code, 200)
        self.assertTrue(export.content.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
