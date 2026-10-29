import unittest

from pipeline import network_analysis as na


def route(period, origin, destination, passengers, scope="domestic", asm=None):
    return {"period": period, "year": int(period[:4]), "month": int(period[5:7]), "origin": origin,
            "destination": destination, "route_id": f"{origin}-{destination}",
            "market_id": "-".join(sorted([origin, destination])), "scope": scope, "passengers": passengers,
            "seats": passengers * 2, "asm": asm if asm is not None else passengers * 100,
            "rpm": passengers * 80, "departures_performed": 1, "departures_scheduled": 1}


class NetworkAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rows = [route(f"2019-{m:02d}-01", "ATL", "LGA", 10) for m in range(1, 13)]
        self.rows += [route(f"2019-{m:02d}-01", "DTW", "MSP", 5) for m in range(1, 13)]
        months = [f"2025-{m:02d}-01" for m in range(6, 13)] + [f"2026-{m:02d}-01" for m in range(1, 6)]
        self.rows += [route(p, "ATL", "LGA", 15) for p in months]
        self.rows += [route(p, "ATL", "LHR", 4, scope="international") for p in months]

    def test_ttm_window_is_latest_twelve_months(self):
        self.assertEqual(na.ttm_window(self.rows), ("2025-06-01", "2026-05-01"))

    def test_incomplete_window_is_rejected(self):
        with self.assertRaises(ValueError):
            na.ttm_window([r for r in self.rows if r["period"] != "2025-09-01"])

    def test_market_comparison_flags_new_and_exited_markets(self):
        markets = {m["market_id"]: m for m in na.market_comparison(self.rows, "2025-06-01", "2026-05-01")}
        self.assertEqual(markets["ATL-LGA"]["passenger_change"], 60)
        self.assertEqual(markets["ATL-LHR"]["status"], "new")
        self.assertEqual(markets["DTW-MSP"]["status"], "exited")

    def test_route_layer_drops_routes_without_coordinates_and_counts_them(self):
        airports = [{"airport_code": "ATL", "latitude": 33.6, "longitude": -84.4, "airport_name": "Atlanta"},
                    {"airport_code": "LGA", "latitude": 40.8, "longitude": -73.9, "airport_name": "LaGuardia"},
                    {"airport_code": "LHR", "latitude": None, "longitude": None}]
        layer, missing = na.route_layer(self.rows, airports, "2025-06-01", "2026-05-01")
        self.assertEqual([r["route_id"] for r in layer], ["ATL-LGA"])
        self.assertEqual(missing, 1)
        self.assertEqual(layer[0]["passengers"], 180)

    def test_structure_reports_international_share(self):
        ttm = [s for s in na.network_structure_by_year(self.rows, "2025-06-01", "2026-05-01") if s["window"] == "TTM"][0]
        self.assertEqual(ttm["months"], 12)
        self.assertAlmostEqual(ttm["international_asm_share"], 400 / 1900)


if __name__ == "__main__":
    unittest.main()
