import csv
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipeline import fpa_model


def synthetic_quarters(first_year=2021, last_label="2026Q3", noise=0.0):
    rows = []
    last = fpa_model.q_index(last_label)
    for i in range(first_year * 4, last + 1):
        year, quarter = i // 4, i % 4 + 1
        season = [0.9, 1.05, 1.1, 0.95][quarter - 1]
        asm = 50e9 * season * (1.04 ** (year - first_year)) * (1 + noise * math.sin(i))
        lf = 0.80 + 0.02 * (quarter == 3)
        yld = 0.18 * (1.02 ** (year - first_year))
        rpm, gallons, price = asm * lf, asm / 80, 2.6 + 0.1 * math.cos(i)
        pax = rpm * yld
        nonpax, exfuel, fuel = pax * 0.12, asm * 0.11, gallons * price
        rows.append({"period_label": f"{year}Q{quarter}", "scope": "system", "asm": asm, "rpm": rpm,
                     "pax_revenue": pax, "non_pax_mainline_revenue": nonpax, "mainline_expense_ex_fuel": exfuel,
                     "scheduled_fuel_gallons": gallons, "scheduled_fuel_cost": fuel,
                     "mainline_operating_income": pax + nonpax - exfuel - fuel})
    return rows


class FpaModelTests(unittest.TestCase):
    def run_model(self, rows):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with patch.object(fpa_model, "PROCESSED", Path(tmp.name)):
            result = fpa_model.build_fpa_model(rows)
        return result, Path(tmp.name)

    def test_drivers_rebuild_operating_income_exactly(self):
        row = synthetic_quarters()[0]
        out = fpa_model.outcomes(fpa_model.drivers_from_actuals(row))
        self.assertAlmostEqual(out["operating_income"], row["mainline_operating_income"], delta=1e-3)

    def test_base_is_seasonal_naive_by_driver(self):
        rows = synthetic_quarters()
        history = {fpa_model.q_index(r["period_label"]): fpa_model.drivers_from_actuals(r) for r in rows}
        origin = fpa_model.q_index("2025Q2")
        path = fpa_model.forecast(history, origin, 4)
        for target, point in path.items():
            for driver, value in point.items():
                self.assertAlmostEqual(value, history[target - 4][driver])

    def test_method_comparison_covers_every_method_and_drift_recovers_constant_growth(self):
        result, out = self.run_model(synthetic_quarters())
        with (out / "analysis_forecast_method_comparison.csv").open() as f:
            rows = [r for r in csv.DictReader(f) if r["horizon"] == "all"]
        self.assertEqual({r["method"] for r in rows}, set(fpa_model.METHODS))
        drift = next(r for r in rows if r["method"] == "median_4q_yoy_drift")
        self.assertLess(float(drift["revenue_mape"]), 1e-9)
        self.assertEqual(result["base_method"], "seasonal_naive")
        self.assertIn("FUEL", result["scenario_next4_operating_income"])

    def test_forecast_uses_only_information_up_to_origin(self):
        rows = synthetic_quarters()
        history = {fpa_model.q_index(r["period_label"]): fpa_model.drivers_from_actuals(r) for r in rows}
        origin = fpa_model.q_index("2024Q4")
        before = fpa_model.forecast(history, origin, 4)
        tampered = dict(history)
        for i in range(origin + 1, max(history) + 1):
            tampered[i] = {k: v * 5 for k, v in history[i].items()}
        self.assertEqual(before, fpa_model.forecast(tampered, origin, 4))

    def test_bridge_steps_sum_to_total_change(self):
        result, out = self.run_model(synthetic_quarters(noise=0.05))
        with (out / "analysis_operating_income_bridge.csv").open() as f:
            steps = list(csv.DictReader(f))
        for b in result["bridges"]:
            total = sum(float(s["operating_income_effect"]) for s in steps
                        if s["from_period"] == b["from_period"] and s["to_period"] == b["to_period"])
            self.assertAlmostEqual(b["start_operating_income"] + total, b["end_operating_income"], delta=1e-3)

    def test_scenarios_bracket_the_base_case(self):
        result, _ = self.run_model(synthetic_quarters())
        sc = result["scenario_next4_operating_income"]
        self.assertLess(sc["DOWN"], result["base_next4_operating_income"])
        self.assertGreater(sc["UP"], result["base_next4_operating_income"])

    def test_budget_is_forecast_from_prior_q4(self):
        _, out = self.run_model(synthetic_quarters())
        with (out / "fact_budget_forecast.csv").open() as f:
            budget = [r for r in csv.DictReader(f) if r["scenario_id"] == "BUD" and r["period"] == "2025Q2"]
        self.assertTrue(budget)
        self.assertEqual({r["forecast_origin"] for r in budget}, {"2024Q4"})

    def test_short_history_is_rejected(self):
        with self.assertRaises(ValueError):
            fpa_model.build_fpa_model(synthetic_quarters(first_year=2026))


if __name__ == "__main__":
    unittest.main()
