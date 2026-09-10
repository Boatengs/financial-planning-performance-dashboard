from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import unittest

from pipeline.transtats import TABLE_IDS, form_url, vq_encode

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, filename: str):
    spec = spec_from_file_location(name, ROOT / "scripts" / filename)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SourceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = load_script("download_t100_history", "download_t100_history.py")
        cls.current = load_script("download_official_sources", "download_official_sources.py")

    def test_transtats_history_covers_2019_2026(self):
        self.assertEqual(set(self.history.SUPPORTED_YEARS), set(range(2019, 2027)))
        self.assertEqual(TABLE_IDS, {"domestic": 259, "international": 261})

    def test_transtats_form_urls_are_exact_first_party_pages(self):
        for scope, table_id in TABLE_IDS.items():
            url = form_url(scope)
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "transtats.bts.gov")
            self.assertEqual(parsed.path, "/DL_SelectFields.aspx")
            self.assertEqual(query["gnoyr_VQ"], [vq_encode(str(table_id))])
            self.assertIn("QO_fu146_anzr", query)

    def test_current_fixed_source_catalog_uses_expected_publishers_and_domains(self):
        allowed_hosts = {
            "data.sec.gov",
            "d18rn0p25nwr6d.cloudfront.net",
            "nfdc.faa.gov",
        }
        self.assertEqual(len(self.current.SOURCES), 4)
        self.assertEqual({source[1] for source in self.current.SOURCES}, {"financial", "network"})
        for label, group, url, destination in self.current.SOURCES:
            parsed = urlparse(url)
            self.assertIn(group, {"financial", "network"}, label)
            self.assertEqual(parsed.scheme, "https", label)
            self.assertIn(parsed.netloc, allowed_hosts, label)
            self.assertTrue(str(destination).startswith(str(self.current.RAW)), label)

    def test_source_domain_selection_is_exact(self):
        financial = self.current.select_sources("financial")
        network = self.current.select_sources("network")
        all_sources = self.current.select_sources("all")

        self.assertEqual(len(financial), 3)
        self.assertEqual(len(network), 1)
        self.assertEqual(len(all_sources), 4)
        self.assertTrue(all(source[1] == "financial" for source in financial))
        self.assertTrue(all(source[1] == "network" for source in network))
        self.assertEqual(set(financial + network), set(all_sources))


if __name__ == "__main__":
    unittest.main()
