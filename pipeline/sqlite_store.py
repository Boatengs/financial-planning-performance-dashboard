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
        SUM(passengers) AS passengers,
        SUM(seats) AS seats,
        SUM(asm) AS asm,
        SUM(rpm) AS rpm,
        CASE WHEN SUM(asm) <> 0 THEN 1.0 * SUM(rpm) / SUM(asm) END AS load_factor,
        SUM(departures_performed) AS departures_performed,
        SUM(departures_scheduled) AS departures_scheduled,
        CASE WHEN SUM(departures_scheduled) <> 0 THEN 1.0 * SUM(departures_performed) / SUM(departures_scheduled) END AS completion_rate
    FROM fact_route_monthly
    GROUP BY route_id, origin, destination, scope;

    CREATE VIEW vw_financial_kpi_long AS
    SELECT metric_id, metric_name, domain, period_end, period_type, value, unit, source
    FROM fact_financial_actual
    UNION ALL
    SELECT metric_id, metric_name, domain, period_end, period_type, value, unit, source
    FROM fact_financial_kpi_derived;

    CREATE VIEW vw_financial_actual_latest AS
    SELECT f.*
    FROM fact_financial_actual f
    JOIN (
        SELECT metric_id, period_end, MAX(filed_date) AS max_filed_date
        FROM fact_financial_actual
        GROUP BY metric_id, period_end
    ) x
    ON f.metric_id = x.metric_id AND f.period_end = x.period_end AND f.filed_date = x.max_filed_date;
    """)
    conn.commit()
    conn.close()
    return db_path
