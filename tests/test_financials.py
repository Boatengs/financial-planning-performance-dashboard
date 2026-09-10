from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipeline import financials


class FinancialPeriodTests(unittest.TestCase):
    def test_frame_period_parses_fiscal_and_quarter_frames(self):
        self.assertEqual(financials.frame_period("CY2025"), ("2025-12-31", "FY"))
        self.assertEqual(financials.frame_period("CY2026Q1"), ("2026-03-31", "Q1"))
        self.assertEqual(financials.frame_period("CY2026Q2I"), ("2026-06-30", "Q2"))
        self.assertEqual(financials.frame_period("CY2026Q3"), ("2026-09-30", "Q3"))
        self.assertEqual(financials.frame_period("CY2026Q4"), ("2026-12-31", "Q4"))
        self.assertEqual(financials.frame_period("FY2026"), (None, None))
        self.assertEqual(financials.frame_period(None), (None, None))

    def test_derived_kpis_use_compatible_periods(self):
        rows = [
            {"metric_id": "revenue", "period_end": "2024-12-31", "period_type": "FY", "value": 100.0},
            {"metric_id": "operating_income", "period_end": "2024-12-31", "period_type": "FY", "value": 10.0},
            {"metric_id": "revenue", "period_end": "2025-12-31", "period_type": "FY", "value": 120.0},
            {"metric_id": "operating_income", "period_end": "2025-12-31", "period_type": "FY", "value": 18.0},
            {"metric_id": "revenue", "period_end": "2025-03-31", "period_type": "Q1", "value": 30.0},
        ]
        with TemporaryDirectory() as tmp, patch.object(financials, "PROCESSED", Path(tmp)):
            derived = financials.build_financial_derived(rows)

        values = {(r["metric_id"], r["period_end"], r["period_type"]): r["value"] for r in derived}
        self.assertAlmostEqual(values[("operating_margin", "2024-12-31", "FY")], 0.10)
        self.assertAlmostEqual(values[("operating_margin", "2025-12-31", "FY")], 0.15)
        self.assertAlmostEqual(values[("revenue_growth_yoy", "2025-12-31", "FY")], 0.20)
        self.assertNotIn(("revenue_growth_yoy", "2025-03-31", "Q1"), values)


if __name__ == "__main__":
    unittest.main()
