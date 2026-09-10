from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import io
import unittest
from unittest.mock import patch
import zipfile

from pipeline import airports


def make_faa_zip(path: Path):
    fields = [
        "ARPT_ID", "ARPT_NAME", "CITY", "STATE_CODE", "STATE_NAME", "COUNTRY_CODE",
        "LAT_DECIMAL", "LONG_DECIMAL", "ELEV", "EFF_DATE"
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerow({
        "ARPT_ID": "ATL",
        "ARPT_NAME": "Hartsfield-Jackson Atlanta International",
        "CITY": "Atlanta",
        "STATE_CODE": "GA",
        "STATE_NAME": "Georgia",
        "COUNTRY_CODE": "US",
        "LAT_DECIMAL": "33.6407",
        "LONG_DECIMAL": "-84.4277",
        "ELEV": "1026",
        "EFF_DATE": "2026-09-03",
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("APT_BASE.csv", buffer.getvalue())


def make_bts_csv(path: Path):
    fields = [
        "Airport", "AirportName", "AirportCityName", "AirportStateCode", "AirportStateName",
        "AirportCountryCodeISO", "AirportCountryName", "CityMarketName", "Latitude", "Longitude",
        "AirportIsLatest", "AirportStartDate",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "Airport": "ATL",
            "AirportName": "Atlanta International",
            "AirportCityName": "Atlanta, GA",
            "AirportStateCode": "GA",
            "AirportStateName": "Georgia",
            "AirportCountryCodeISO": "US",
            "AirportCountryName": "United States",
            "CityMarketName": "Atlanta, GA",
            "Latitude": "33.64",
            "Longitude": "-84.43",
            "AirportIsLatest": "1",
            "AirportStartDate": "2000-01-01",
        })
        writer.writerow({
            "Airport": "LHR",
            "AirportName": "London Heathrow",
            "AirportCityName": "London, United Kingdom",
            "AirportCountryCodeISO": "GB",
            "AirportCountryName": "United Kingdom",
            "CityMarketName": "London",
            "Latitude": "51.4700",
            "Longitude": "-0.4543",
            "AirportIsLatest": "1",
            "AirportStartDate": "2000-01-01",
        })


class AirportDimensionTests(unittest.TestCase):
    def test_bts_coordinates_take_precedence_and_faa_can_fill_elevation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            processed = root / "processed"
            make_faa_zip(raw / "faa_airports_2026-09-03.zip")
            make_bts_csv(raw / "bts_master_coordinate.csv")
            detailed = [{
                "origin": "ATL",
                "destination": "LHR",
                "origin_city_name": "Atlanta, GA",
                "destination_city_name": "London, UK",
                "origin_wac": 34,
                "destination_wac": 493,
            }]
            route_rows = [{"origin": "ATL", "destination": "LHR"}]
            with patch.object(airports, "RAW", raw), patch.object(airports, "PROCESSED", processed):
                rows, codes, bts_path = airports.build_airport_dimension(detailed, route_rows)

        by_code = {row["airport_code"]: row for row in rows}
        self.assertEqual(codes, {"ATL", "LHR"})
        self.assertEqual(bts_path.name, "bts_master_coordinate.csv")
        self.assertEqual(by_code["ATL"]["coordinate_source"], "BTS Master Coordinate")
        self.assertAlmostEqual(by_code["ATL"]["latitude"], 33.64)
        self.assertEqual(by_code["ATL"]["elevation_ft"], 1026.0)
        self.assertEqual(by_code["LHR"]["coordinate_status"], "resolved_bts_master_coordinate")

    def test_unresolved_airport_remains_explicitly_pending(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            processed = root / "processed"
            make_faa_zip(raw / "faa_airports_2026-09-03.zip")
            detailed = [{
                "origin": "ATL",
                "destination": "LHR",
                "origin_city_name": "Atlanta, GA",
                "destination_city_name": "London, UK",
                "origin_wac": 34,
                "destination_wac": 493,
            }]
            route_rows = [{"origin": "ATL", "destination": "LHR"}]
            with patch.object(airports, "RAW", raw), patch.object(airports, "PROCESSED", processed):
                rows, _, bts_path = airports.build_airport_dimension(detailed, route_rows)

        by_code = {row["airport_code"]: row for row in rows}
        self.assertIsNone(bts_path)
        self.assertEqual(by_code["ATL"]["coordinate_status"], "resolved_faa")
        self.assertEqual(by_code["LHR"]["coordinate_status"], "pending_bts_master_coordinate")
        self.assertIsNone(by_code["LHR"]["latitude"])
        self.assertIsNone(by_code["LHR"]["longitude"])


if __name__ == "__main__":
    unittest.main()
