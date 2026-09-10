import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipeline import network_history


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fixture_rows():
    detail = {
        "year": "2025",
        "month": "7",
        "origin": "ATL",
        "destination": "JFK",
        "carrier_code": "DL",
        "carrier_entity_code": "19790",
        "service_class": "F",
        "aircraft_group": "6",
        "aircraft_type": "694",
        "aircraft_configuration": "1",
        "scope": "domestic",
        "source_file": "DB28SEG.DD.WAC.202501.202512.REL01.03MAR2026.zip",
        "source_release_date": "2026-03-03",
    }
    route = {
        "period": "2025-07-01",
        "origin": "ATL",
        "destination": "JFK",
        "route_id": "ATL-JFK",
        "scope": "domestic",
        "distance_miles": "760",
        "departures_performed": "9",
        "departures_scheduled": "10",
        "seats": "1000",
        "passengers": "800",
        "asm": "760000",
        "rpm": "608000",
        "freight_pounds": "500",
        "mail_pounds": "50",
    }
    network = {
        "period": "2025-07-01",
        "scope": "domestic",
        "passengers": "800",
        "seats": "1000",
        "asm": "760000",
        "rpm": "608000",
        "load_factor": "0.8",
        "departures_performed": "9",
        "departures_scheduled": "10",
        "completion_rate": "0.9",
        "freight_pounds": "500",
        "mail_pounds": "50",
    }
    return detail, route, network


def materialize_fixture(processed: Path, *, duplicate_detail: bool = False):
    detail, route, network = fixture_rows()
    detail_rows = [detail, dict(detail)] if duplicate_detail else [detail]
    write_csv(processed / "fact_route_aircraft_monthly.csv", detail_rows)
    write_csv(processed / "fact_route_monthly.csv", [route])
    write_csv(processed / "fact_network_kpi_monthly.csv", [network])
    write_csv(processed / "dim_airport.csv", [{"airport_code": "ATL"}, {"airport_code": "JFK"}])
    write_csv(processed / "dim_route.csv", [{"route_id": "ATL-JFK"}])
    (processed / "network_history_summary.json").write_text(
        json.dumps({"route_month_rows": 1, "aircraft_detail_rows": len(detail_rows)}),
        encoding="utf-8",
    )


class NetworkHistoryValidationTests(unittest.TestCase):
    def test_validator_reconciles_network_tables(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            materialize_fixture(processed)
            with patch.object(network_history, "PROCESSED", processed), patch.object(network_history, "ROOT", root):
                report = network_history.validate_network_history(expected_years=[2025])

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["reporting_carriers"], ["DL"])
        self.assertEqual(report["route_month_rows"], 1)
        self.assertEqual(report["annual_rows_with_unknown_release_date"], 0)

    def test_validator_rejects_duplicate_aircraft_detail_keys(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            materialize_fixture(processed, duplicate_detail=True)
            with patch.object(network_history, "PROCESSED", processed), patch.object(network_history, "ROOT", root):
                with self.assertRaisesRegex(AssertionError, "duplicate natural keys"):
                    network_history.validate_network_history(expected_years=[2025])


if __name__ == "__main__":
    unittest.main()
