import csv
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from pipeline import form41, unit_economics


def write_zip(path: Path, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("T_SCHEDULE.csv", buffer.getvalue())


def p12_row(carrier, region, year, quarter, **amounts):
    row = {field: "0" for field in form41.P12_AMOUNT_FIELDS}
    row.update({"YEAR": str(year), "QUARTER": str(quarter), "UNIQUE_CARRIER": carrier, "REGION": region,
                "UNIQUE_CARRIER_ENTITY": f"{carrier}-{region}"})
    row.update({k: str(v) for k, v in amounts.items()})
    return row


def fuel_row(carrier, year, month, dom_gal, dom_cost, int_gal, int_cost):
    return {"YEAR": year, "QUARTER": (month - 1) // 3 + 1, "MONTH": month, "UNIQUE_CARRIER": carrier,
            "SDOMT_GALLONS": dom_gal, "SINT_GALLONS": int_gal, "TS_GALLONS": dom_gal + int_gal,
            "TOTAL_GALLONS": dom_gal + int_gal, "SDOMT_COST": dom_cost, "SINT_COST": int_cost,
            "TS_COST": dom_cost + int_cost, "TOTAL_COST": dom_cost + int_cost}


class Form41Tests(unittest.TestCase):
    def test_regions_map_to_t100_scopes(self):
        self.assertEqual(form41.region_scope("D"), "domestic")
        self.assertEqual(form41.region_scope("Domestic"), "domestic")
        for region in ("A", "P", "L", "Atlantic", "Pacific", "Latin America", "International"):
            self.assertEqual(form41.region_scope(region), "international", region)
        self.assertIsNone(form41.region_scope("System"))

    def test_p12_filters_dl_converts_thousands_and_rolls_up_system(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "p12.zip"
            write_zip(path, [
                p12_row("DL", "D", 2025, 1, OP_REVENUES=1000, TRANS_REV_PAX=800, OP_EXPENSES=900),
                p12_row("DL", "A", 2025, 1, OP_REVENUES=400, TRANS_REV_PAX=350, OP_EXPENSES=380),
                p12_row("UA", "D", 2025, 1, OP_REVENUES=5000),
            ])
            rows, skipped = form41.parse_p12([path])
        self.assertEqual(skipped, {})
        self.assertEqual(len(rows), 2)
        totals = {r["scope"]: r for r in form41.quarterly_pnl_by_scope(rows)}
        self.assertEqual(totals["domestic"]["op_revenues"], 1_000_000)
        self.assertEqual(totals["system"]["op_revenues"], 1_400_000)
        self.assertEqual(totals["system"]["trans_rev_pax"], 1_150_000)

    def test_unmapped_region_is_reported_not_counted(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "p12.zip"
            write_zip(path, [p12_row("DL", "S", 2025, 1, OP_REVENUES=1)])
            rows, skipped = form41.parse_p12([path])
        self.assertEqual(rows, [])
        self.assertEqual(skipped, {"S": 1})

    def test_fuel_quarter_needs_three_months(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "fuel.zip"
            write_zip(path, [fuel_row("DL", 2025, m, 100, 250, 50, 130) for m in (1, 2, 3)]
                      + [fuel_row("DL", 2025, 4, 100, 250, 50, 130)])
            q = {(r["period_label"], r["scope"]): r for r in form41.quarterly_fuel_by_scope(form41.parse_fuel([path]))}
        self.assertEqual(q[("2025Q1", "system")]["months_reported"], 3)
        self.assertEqual(q[("2025Q1", "system")]["scheduled_fuel_gallons"], 450)
        self.assertEqual(q[("2025Q2", "system")]["months_reported"], 1)


class UnitEconomicsTests(unittest.TestCase):
    def test_unit_measures_use_mainline_numerators_over_t100_capacity(self):
        route_rows = [
            {"year": 2025, "month": m, "scope": "domestic", "asm": 1000, "rpm": 800, "passengers": 10, "seats": 12,
             "departures_performed": 1, "departures_scheduled": 1} for m in (1, 2, 3)
        ]
        pnl = [{"year": 2025, "quarter": 1, "scope": "domestic", "trans_rev_pax": 300, "op_revenues": 400,
                "trans_revenue": 40, "op_expenses": 380, "trans_expenses": 50}]
        fuel = [{"year": 2025, "quarter": 1, "scope": "domestic", "months_reported": 3,
                 "scheduled_fuel_cost": 90, "scheduled_fuel_gallons": 30}]
        with TemporaryDirectory() as tmp, patch.object(unit_economics, "PROCESSED", Path(tmp)):
            rows, skipped = unit_economics.build_unit_economics(route_rows, pnl, fuel)
        self.assertEqual(skipped, [])
        r = rows[0]
        self.assertEqual(r["asm"], 3000)
        self.assertEqual(r["mainline_revenue"], 360)
        self.assertEqual(r["mainline_expense"], 330)
        self.assertAlmostEqual(r["trasm_cents"], 12.0)
        self.assertAlmostEqual(r["casm_ex_fuel_cents"], 8.0)
        self.assertAlmostEqual(r["yield_cents"], 12.5)
        self.assertAlmostEqual(r["fuel_cost_per_gallon"], 3.0)

    def test_partial_quarters_are_skipped(self):
        route_rows = [{"year": 2026, "month": 4, "scope": "domestic", "asm": 1, "rpm": 1, "passengers": 1,
                       "seats": 1, "departures_performed": 1, "departures_scheduled": 1}]
        pnl = [{"year": 2026, "quarter": 2, "scope": "domestic", "trans_rev_pax": 1, "op_revenues": 1,
                "trans_revenue": 0, "op_expenses": 1, "trans_expenses": 0}]
        with TemporaryDirectory() as tmp, patch.object(unit_economics, "PROCESSED", Path(tmp)):
            rows, skipped = unit_economics.build_unit_economics(route_rows, pnl, [])
        self.assertEqual(rows, [])
        self.assertEqual(skipped[0]["t100_months"], 1)


if __name__ == "__main__":
    unittest.main()
