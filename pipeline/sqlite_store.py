from __future__ import annotations

import csv
import sqlite3

from .config import PROCESSED
from .io_utils import coerce_sql, infer_sql_type


def build_sqlite(table_files):
    db_path = PROCESSED / "delta_fpna_foundation.sqlite"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=DELETE")
    for table_name, csv_path in table_files.items():
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fields = reader.fieldnames or []
        if not fields:
            continue
        types = {c: infer_sql_type([r[c] for r in rows]) for c in fields}
        cols = ", ".join([f'"{c}" {types[c]}' for c in fields])
        conn.execute(f'CREATE TABLE "{table_name}" ({cols})')
        if rows:
            placeholders = ",".join(["?"] * len(fields))
            payload = [[coerce_sql(r[c], types[c]) for c in fields] for r in rows]
            conn.executemany(f'INSERT INTO "{table_name}" VALUES ({placeholders})', payload)

    conn.execute("CREATE INDEX idx_route_period ON fact_route_monthly(period, origin, destination)")
    conn.execute("CREATE INDEX idx_route_id_period ON fact_route_monthly(route_id, period)")
    conn.execute("CREATE INDEX idx_fin_period ON fact_financial_actual(period_end, metric_id)")
    conn.execute("CREATE INDEX idx_fin_derived_period ON fact_financial_kpi_derived(period_end, metric_id)")
    conn.execute("CREATE INDEX idx_airport_code ON dim_airport(airport_code)")
    if "fact_unit_economics_quarterly" in table_files:
        conn.execute("CREATE INDEX idx_unit_econ ON fact_unit_economics_quarterly(period_label, scope)")

    conn.executescript("""
    CREATE VIEW vw_network_monthly AS
    SELECT
        period,
        SUM(passengers) AS passengers,
        SUM(seats) AS seats,
        SUM(asm) AS asm,
        SUM(rpm) AS rpm,
        CASE WHEN SUM(asm) <> 0 THEN 1.0 * SUM(rpm) / SUM(asm) END AS load_factor,
        SUM(departures_performed) AS departures_performed,
        SUM(departures_scheduled) AS departures_scheduled,
        CASE WHEN SUM(departures_scheduled) <> 0 THEN 1.0 * SUM(departures_performed) / SUM(departures_scheduled) END AS completion_rate,
        SUM(freight_pounds) AS freight_pounds
    FROM fact_route_monthly
    GROUP BY period;

    CREATE VIEW vw_route_12m AS
    SELECT
        route_id, origin, destination, scope, MAX(distance_miles) AS distance_miles,
        MIN(period) AS window_start, MAX(period) AS window_end,
        SUM(passengers) AS passengers,
        SUM(seats) AS seats,
        SUM(asm) AS asm,
        SUM(rpm) AS rpm,
        CASE WHEN SUM(asm) <> 0 THEN 1.0 * SUM(rpm) / SUM(asm) END AS load_factor,
        SUM(departures_performed) AS departures_performed,
        SUM(departures_scheduled) AS departures_scheduled,
        CASE WHEN SUM(departures_scheduled) <> 0 THEN 1.0 * SUM(departures_performed) / SUM(departures_scheduled) END AS completion_rate
    FROM fact_route_monthly
    WHERE period > date((SELECT MAX(period) FROM fact_route_monthly), '-12 months')
    GROUP BY route_id, origin, destination, scope;

    CREATE VIEW vw_financial_kpi_long AS
    SELECT metric_id, metric_name, domain, period_label, period_end, period_type, value, unit, method AS lineage, source
    FROM fact_financial_actual
    UNION ALL
    SELECT metric_id, metric_name, domain, period_label, period_end, period_type, value, unit, formula AS lineage, source
    FROM fact_financial_kpi_derived;

    CREATE VIEW vw_financial_quarterly_wide AS
    SELECT period_label, period_end,
        MAX(CASE WHEN metric_id = 'revenue' THEN value END) AS revenue,
        MAX(CASE WHEN metric_id = 'operating_expenses' THEN value END) AS operating_expenses,
        MAX(CASE WHEN metric_id = 'operating_income' THEN value END) AS operating_income,
        MAX(CASE WHEN metric_id = 'net_income' THEN value END) AS net_income,
        MAX(CASE WHEN metric_id = 'fuel_costs' THEN value END) AS fuel_costs,
        MAX(CASE WHEN metric_id = 'labor_costs' THEN value END) AS labor_costs,
        MAX(CASE WHEN metric_id = 'operating_cash_flow' THEN value END) AS operating_cash_flow,
        MAX(CASE WHEN metric_id = 'capex_total' THEN value END) AS capex_total,
        MAX(CASE WHEN metric_id = 'cash' THEN value END) AS cash,
        MAX(CASE WHEN metric_id = 'debt_total' THEN value END) AS debt_total
    FROM fact_financial_actual
    WHERE period_type <> 'FY'
    GROUP BY period_label, period_end;
    """)
    conn.commit()
    conn.close()
    return db_path
