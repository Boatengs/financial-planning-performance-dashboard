from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import urllib.error

from pipeline import http_download


class HttpDownloadTests(unittest.TestCase):
    def test_sec_uses_declared_contact_user_agent(self):
        with patch.dict("os.environ", {"SEC_USER_AGENT": "Example App data@example.com"}):
            headers = http_download.request_headers(
                "https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json"
            )
        self.assertEqual(headers["User-Agent"], "Example App data@example.com")
        self.assertIn("application/json", headers["Accept"])

    def test_bts_uses_browser_compatible_headers_and_referer(self):
        headers = http_download.request_headers(
            "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/example.zip"
        )
        self.assertTrue(headers["User-Agent"].startswith("Mozilla/5.0"))
        self.assertEqual(headers["Referer"], "https://www.bts.gov/")
        self.assertIn("application/zip", headers["Accept"])

    def test_zip_payload_validation_rejects_html_response(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.zip"
            path.write_bytes(b"<html>blocked</html>")
            with self.assertRaisesRegex(ValueError, "not a ZIP archive"):
                http_download._validate_payload(path)

    def test_bts_403_falls_back_to_curl(self):
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "source.zip"

            def fake_curl(url, partial, timeout):
                partial.write_bytes(b"PK\x03\x04fixture")

            forbidden = urllib.error.HTTPError(
                "https://www.bts.gov/example.zip", 403, "Forbidden", hdrs=None, fp=None
            )
            with patch.object(http_download, "_download_with_urllib", side_effect=forbidden), patch.object(
                http_download, "_download_with_curl", side_effect=fake_curl
            ) as curl_mock:
                http_download.download_file(
                    "https://www.bts.gov/example.zip", destination, retries=1
                )

        curl_mock.assert_called_once()
        self.assertTrue(destination.exists())


if __name__ == "__main__":
    unittest.main()
