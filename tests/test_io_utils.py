from pathlib import Path
import unittest

from pipeline.io_utils import release_date_from_name


class ReleaseDateParsingTests(unittest.TestCase):
    def test_annual_bts_release_date_is_parsed(self):
        path = Path("DB28SEG.FD.WAC.202201.202212.REL01.19SEP2023.zip")
        self.assertEqual(release_date_from_name(path), "2023-09-19")

    def test_current_rolling_release_uses_known_release_date(self):
        path = Path("current_202506_202605.zip")
        self.assertEqual(release_date_from_name(path), "2026-08-04")

    def test_unknown_filename_has_explicit_low_precedence_date(self):
        self.assertEqual(release_date_from_name(Path("unversioned.zip")), "1900-01-01")


if __name__ == "__main__":
    unittest.main()
