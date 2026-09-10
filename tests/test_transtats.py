from urllib.parse import parse_qs
import unittest
from unittest.mock import patch

from pipeline import transtats


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def read(self):
        return self.body


class FakeOpener:
    def __init__(self, html: str, payload: bytes):
        self.html = html.encode()
        self.payload = payload
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        if len(self.requests) == 1:
            return FakeResponse(self.html)
        return FakeResponse(self.payload)


def form_fixture():
    hidden = (
        '<input type="hidden" name="__VIEWSTATE" value="state-token" />'
        '<input type="hidden" name="__VIEWSTATEGENERATOR" value="generator-token" />'
        '<input type="hidden" name="__EVENTVALIDATION" value="validation-token" />'
    )
    checkboxes = "".join(
        f'<input type="checkbox" name="{field}" />'
        for field in sorted(transtats.REQUIRED_FORM_FIELDS)
    )
    years = "".join(f'<option value="{year}">{year}</option>' for year in range(2019, 2027))
    return f"<html><form>{hidden}{checkboxes}<select>{years}</select></form></html>"


class TranStatsTests(unittest.TestCase):
    def test_vq_table_id_encoding(self):
        self.assertEqual(transtats.vq_encode("259"), "FIM")
        self.assertEqual(transtats.vq_encode("261"), "FJE")

    def test_parse_form_finds_state_fields_variables_and_years(self):
        hidden, fields, years = transtats._parse_form(form_fixture())
        self.assertEqual(hidden["__VIEWSTATE"], "state-token")
        self.assertEqual(set(fields), transtats.REQUIRED_FORM_FIELDS)
        self.assertEqual(years, {str(year) for year in range(2019, 2027)})

    def test_fetch_posts_required_fields_for_requested_year(self):
        opener = FakeOpener(form_fixture(), b"PKfixture")
        with patch("pipeline.transtats.urllib.request.build_opener", return_value=opener):
            payload = transtats._fetch_once("domestic", 2025, timeout=30)

        self.assertEqual(payload, b"PKfixture")
        self.assertEqual(len(opener.requests), 2)
        post = opener.requests[1]
        form = parse_qs(post.data.decode())
        self.assertEqual(form["cboYear"], ["2025"])
        self.assertEqual(form["cboGeography"], ["All"])
        self.assertEqual(form["cboPeriod"], ["All"])
        self.assertEqual(form["chkDownloadZip"], ["on"])
        for field in transtats.REQUIRED_FORM_FIELDS:
            self.assertEqual(form[field], ["on"])

    def test_fetch_rejects_unoffered_year(self):
        opener = FakeOpener(form_fixture(), b"PKfixture")
        with patch("pipeline.transtats.urllib.request.build_opener", return_value=opener):
            with self.assertRaisesRegex(RuntimeError, "does not offer year 2018"):
                transtats._fetch_once("domestic", 2018, timeout=30)


if __name__ == "__main__":
    unittest.main()
