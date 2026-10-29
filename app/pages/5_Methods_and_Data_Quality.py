"""Sources, scope, validation status and the metric dictionary."""
import pandas as pd
import streamlit as st

from data import csv, js, page_setup, require_data

page_setup("Methods and Data Quality")
require_data()
qa = js("qa_summary.json")
validation = js("validation_report.json")

st.title("Methods and data quality")
status = validation["status"]
(st.success if status == "PASS" else st.error)(
    f"Validation {status}: {sum(c['pass'] for c in validation['checks'].values())} of "
    f"{len(validation['checks'])} checks passed. Build {qa['build_timestamp_utc']}."
)

st.subheader("Scope")
st.markdown(
    f"- **Consolidated financials**: Delta Air Lines, Inc. from {qa['financial']['source']}, quarters through "
    f"{qa['financial']['latest_quarter_end']}.\n"
    f"- **Network**: T-100 segment data for the DL reporting carrier, {qa['network']['period_min'][:7]} to "
    f"{qa['network']['period_max'][:7]}. Delta Connection regional partners report under their own codes and are "
    "not included.\n"
    "- **Unit economics**: Form 41 P-1.2 and P-12(a) for the same DL entity, divided by T-100 ASMs and RPMs.\n"
    "- **Forecasts and scenarios**: analyst-modeled from these public actuals. Not company guidance."
)

st.subheader("Validation checks")
checks = pd.DataFrame([{"Check": k, "Pass": v["pass"], "Detail": v["detail"]}
                       for k, v in validation["checks"].items()])
st.dataframe(checks, hide_index=True, use_container_width=True)

st.subheader("Sources")
st.dataframe(csv("source_manifest.csv")[["source_name", "local_file", "official_url", "role", "sha256"]],
             hide_index=True, use_container_width=True)

st.subheader("Metric dictionary")
st.dataframe(csv("metric_dictionary.csv"), hide_index=True, use_container_width=True)

st.subheader("How quarterly SEC values were obtained")
methods = pd.DataFrame([{"metric": m, **v} for m, v in qa["financial"]["methods"].items()]).fillna(0)
st.dataframe(methods, hide_index=True, use_container_width=True)
st.caption("reported: a three-month value in a filing. derived_fy_minus_9m: Q4 = full year minus nine months. "
           "derived_ytd_difference: cash-flow quarter = year-to-date minus prior year-to-date. "
           "derived_sum_of_components: total capex = flight equipment + ground and technology.")
