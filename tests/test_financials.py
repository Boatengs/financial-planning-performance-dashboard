from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipeline import financials


def fact(start, end, val, form="10-Q", filed="2025-01-01", frame=None):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed, "accn": f"acc-{end}-{filed}",
            "fy": int(end[:4]), "fp": "", "frame": frame}


def companyfacts(revenue, cash=None, capex_parts=None):
    usd = {"RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": revenue}}}
    if cash:
        usd["CashAndCashEquivalentsAtCarryingValue"] = {"units": {"USD": cash}}
    if capex_parts:
        usd["PaymentsForFlightEquipment"] = {"units": {"USD": capex_parts[0]}}
        usd["PaymentsToAcquireOtherProductiveAssets"] = {"units": {"USD": capex_parts[1]}}
    return {"cik": 27904, "entityName": "DELTA AIR LINES, INC.", "facts": {"us-gaap": usd, "dei": {}}}


class FinancialExtractionTests(unittest.TestCase):
    def test_q4_is_full_year_minus_nine_months(self):
        data = companyfacts([
            fact("2024-01-01", "2024-03-31", 10), fact("2024-04-01", "2024-06-30", 20),
            fact("2024-07-01", "2024-09-30", 30), fact("2024-01-01", "2024-09-30", 60),
            fact("2024-01-01", "2024-12-31", 100, form="10-K"),
        ])
        rows, _ = financials.extract_financial_actuals(data, years=[2024])
        by = {r["period_label"]: r for r in rows if r["metric_id"] == "revenue"}
        self.assertEqual(by["2024Q4"]["value"], 40)
        self.assertEqual(by["2024Q4"]["method"], "derived_fy_minus_9m")
        self.assertEqual(by["2024FY"]["value"], 100)
        self.assertEqual(by["2024Q2"]["method"], "reported")

    def test_cash_flow_quarters_come_from_year_to_date_differences(self):
        data = companyfacts([
            fact("2025-01-01", "2025-03-31", 5), fact("2025-01-01", "2025-06-30", 12),
            fact("2025-01-01", "2025-09-30", 20), fact("2025-01-01", "2025-12-31", 30, form="10-K"),
        ])
        rows, _ = financials.extract_financial_actuals(data, years=[2025])
        by = {r["period_label"]: (r["value"], r["method"]) for r in rows}
        self.assertEqual(by["2025Q1"], (5, "reported"))
        self.assertEqual(by["2025Q2"], (7, "derived_ytd_difference"))
        self.assertEqual(by["2025Q3"], (8, "derived_ytd_difference"))
        self.assertEqual(by["2025Q4"], (10, "derived_fy_minus_9m"))

    def test_latest_filing_wins_for_restated_period(self):
        data = companyfacts([
            fact("2024-01-01", "2024-03-31", 10, filed="2024-04-10"),
            fact("2024-01-01", "2024-03-31", 11, filed="2025-04-10"),
        ])
        rows, _ = financials.extract_financial_actuals(data, years=[2024])
        self.assertEqual([r["value"] for r in rows if r["period_label"] == "2024Q1"], [11])

    def test_instants_are_read_at_quarter_ends_and_year_end(self):
        cash = [{"end": "2024-12-31", "val": 7, "form": "10-K", "filed": "2025-02-01", "accn": "a"},
                {"end": "2024-06-30", "val": 5, "form": "10-Q", "filed": "2024-07-01", "accn": "b"}]
        rows, _ = financials.extract_financial_actuals(companyfacts([], cash=cash), years=[2024])
        by = {r["period_label"]: r["value"] for r in rows if r["metric_id"] == "cash"}
        self.assertEqual(by, {"2024Q2": 5, "2024Q4": 7, "2024FY": 7})

    def test_capex_total_falls_back_to_sum_of_components(self):
        flight = [fact("2026-04-01", "2026-06-30", 30)]
        ground = [fact("2026-04-01", "2026-06-30", 12)]
        rows, _ = financials.extract_financial_actuals(companyfacts([], capex_parts=(flight, ground)), years=[2026])
        capex = [r for r in rows if r["metric_id"] == "capex_total"]
        self.assertEqual(len(capex), 1)
        self.assertEqual(capex[0]["value"], 42)
        self.assertEqual(capex[0]["method"], "derived_sum_of_components")

    def test_alternate_debt_tag_fills_only_missing_periods(self):
        data = companyfacts([])
        usd = data["facts"]["us-gaap"]
        usd["LongTermDebt"] = {"units": {"USD": [
            {"end": "2020-12-31", "val": 28, "form": "10-K", "filed": "2021-02-01", "accn": "a"}]}}
        usd["DebtLongtermAndShorttermCombinedAmount"] = {"units": {"USD": [
            {"end": "2020-06-30", "val": 23, "form": "10-Q", "filed": "2020-07-15", "accn": "b"},
            {"end": "2020-12-31", "val": 99, "form": "10-Q", "filed": "2021-04-15", "accn": "c"}]}}
        rows, _ = financials.extract_financial_actuals(data, years=[2020])
        debt = {r["period_label"]: (r["value"], r["taxonomy_tag"]) for r in rows if r["metric_id"] == "debt_total"}
        self.assertEqual(debt["2020Q2"], (23, "DebtLongtermAndShorttermCombinedAmount"))
        self.assertEqual(debt["2020Q4"], (28, "LongTermDebt"))

    def test_entity_check_rejects_other_companies(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.json"
            path.write_text('{"cik": 4515, "entityName": "AMERICAN AIRLINES", "facts": {}}')
            with self.assertRaises(AssertionError):
                financials.load_companyfacts(path)

    def test_quarterly_reconciliation_reports_differences(self):
        data = companyfacts([
            fact("2024-01-01", "2024-03-31", 10), fact("2024-04-01", "2024-06-30", 20),
            fact("2024-07-01", "2024-09-30", 30), fact("2024-01-01", "2024-09-30", 60),
            fact("2024-01-01", "2024-12-31", 100, form="10-K"),
        ])
        rows, _ = financials.extract_financial_actuals(data, years=[2024])
        checks = financials.quarterly_reconciliation(rows)
        self.assertEqual(checks[0]["difference"], 0)

    def test_derived_kpis_use_matching_periods(self):
        rows = [
            {"metric_id": m, "period_label": label, "period_type": ptype, "fiscal_year": year, "fiscal_quarter": q,
             "period_start": "", "period_end": end, "value": v}
            for m, label, ptype, year, q, end, v in [
                ("revenue", "2024FY", "FY", 2024, "", "2024-12-31", 100.0),
                ("operating_income", "2024FY", "FY", 2024, "", "2024-12-31", 10.0),
                ("revenue", "2025FY", "FY", 2025, "", "2025-12-31", 120.0),
                ("operating_income", "2025FY", "FY", 2025, "", "2025-12-31", 18.0),
                ("operating_cash_flow", "2025FY", "FY", 2025, "", "2025-12-31", 30.0),
                ("capex_total", "2025FY", "FY", 2025, "", "2025-12-31", 12.0),
                ("revenue", "2025Q1", "Q1", 2025, 1, "2025-03-31", 30.0),
            ]
        ]
        with TemporaryDirectory() as tmp, patch.object(financials, "PROCESSED", Path(tmp)):
            derived = financials.build_financial_derived(rows)
        values = {(r["metric_id"], r["period_label"]): r["value"] for r in derived}
        self.assertAlmostEqual(values[("operating_margin", "2024FY")], 0.10)
        self.assertAlmostEqual(values[("operating_margin", "2025FY")], 0.15)
        self.assertAlmostEqual(values[("revenue_growth_yoy", "2025FY")], 0.20)
        self.assertAlmostEqual(values[("free_cash_flow", "2025FY")], 18.0)
        self.assertNotIn(("revenue_growth_yoy", "2025Q1"), values)


if __name__ == "__main__":
    unittest.main()
