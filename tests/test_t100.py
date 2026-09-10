from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from pipeline import t100
from pipeline.config import T100_COLUMNS


def make_row(**overrides):
    base = {name: "" for name in T100_COLUMNS}
    base.update({
        "year": "2025",
        "month": "7",
        "origin": "ATL",
        "origin_numeric_code": "10397",
        "origin_wac": "34",
        "origin_city_name": "Atlanta, GA",
        "destination": "JFK",
        "destination_numeric_code": "12478",
        "destination_wac": "22",
        "destination_city_name": "New York, NY",
        "carrier_code": "DL",
        "carrier_entity_code": "19790",
        "carrier_group_code": "3",
        "distance_miles": "500",
        "service_class": "F",
        "aircraft_group": "6",
        "aircraft_type": "694",
        "aircraft_configuration": "1",
        "departures_performed": "9",
        "departures_scheduled": "10",
        "payload_pounds": "10000",
        "seats": "100",
        "passengers": "75",
        "freight_pounds": "500",
        "mail_pounds": "50",
        "ramp_to_ramp_minutes": "900",
        "airborne_minutes": "800",
        "carrier_wac": "34",
    })
    base.update({k: str(v) for k, v in overrides.items()})
    return "|".join(base[col] for col in T100_COLUMNS) + "|\n"


def write_zip(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("segment.asc", "".join(lines))


class T100Tests(unittest.TestCase):
    def test_parser_filters_to_reporting_carrier_dl(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.01JAN2026.zip"
            write_zip(path, [make_row(carrier_code="AA"), make_row(carrier_code="DL")])
            rows = list(t100.parse_t100_zip(path, "domestic"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["carrier_code"], "DL")
        self.assertEqual(rows[0]["passengers"], 75)
        self.assertEqual(rows[0]["source_release_date"], "2026-01-01")

    def test_later_release_wins_and_route_kpis_reconcile(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            processed = root / "processed"
            (raw / "t100" / "international").mkdir(parents=True)
            write_zip(raw / "t100" / "domestic" / "sample.01JAN2026.zip", [make_row(passengers=70)])
            write_zip(raw / "t100" / "domestic" / "sample.02FEB2026.zip", [make_row(passengers=80)])

            with patch.object(t100, "RAW", raw), patch.object(t100, "PROCESSED", processed):
                detailed, routes, system, _ = t100.build_t100()

        self.assertEqual(len(detailed), 1)
        self.assertEqual(detailed[0]["passengers"], 80)
        self.assertEqual(detailed[0]["source_release_date"], "2026-02-02")
        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route["asm"], 50_000)
        self.assertEqual(route["rpm"], 40_000)
        self.assertAlmostEqual(route["load_factor"], 0.8)
        self.assertAlmostEqual(route["completion_rate"], 0.9)
        self.assertAlmostEqual(route["passengers_per_departure"], 80 / 9)
        self.assertEqual(system[0]["passengers"], 80)
        self.assertAlmostEqual(system[0]["load_factor"], 0.8)

    def test_malformed_segment_row_fails_fast(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.01JAN2026.zip"
            write_zip(path, ["too|few|fields|\n"])
            with self.assertRaisesRegex(ValueError, "expected 28 fields"):
                list(t100.parse_t100_zip(path, "domestic"))


if __name__ == "__main__":
    unittest.main()
