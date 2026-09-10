from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import urlparse
import unittest

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

    def test_historical_t100_manifest_has_complete_2019_2025_coverage(self):
        expected_years = set(range(2019, 2026))
        self.assertEqual(set(self.history.URLS), {"domestic", "international"})
        self.assertEqual(set(self.history.URLS["domestic"]), expected_years)
        self.assertEqual(set(self.history.URLS["international"]), expected_years)

        urls = []
        for scope in ("domestic", "international"):
            for year, url in self.history.URLS[scope].items():
                parsed = urlparse(url)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.netloc, "www.bts.gov")
                self.assertIn(f"{year}01.{year}12", url)
                self.assertTrue(url.endswith(".zip"))
                urls.append(url)
        self.assertEqual(len(urls), 14)
        self.assertEqual(len(set(urls)), 14)

    def test_2022_international_archive_range_is_correct(self):
        self.assertIn("202201.202212", self.history.URLS["international"][2022])

    def test_current_source_catalog_uses_expected_publishers_and_domains(self):
        allowed_hosts = {
            "data.sec.gov",
            "d18rn0p25nwr6d.cloudfront.net",
            "nfdc.faa.gov",
            "www.bts.gov",
        }
        self.assertEqual(len(self.current.SOURCES), 6)
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
        self.assertEqual(len(network), 3)
        self.assertEqual(len(all_sources), 6)
        self.assertTrue(all(source[1] == "financial" for source in financial))
        self.assertTrue(all(source[1] == "network" for source in network))
        self.assertEqual(set(financial + network), set(all_sources))


if __name__ == "__main__":
    unittest.main()
