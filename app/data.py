"""Shared data access and formatting for the Streamlit app. Reads only data/published/."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "data" / "published"

INK = "#1f2937"
MUTED = "#6b7280"
BLUE = "#1d4ed8"
RED = "#b91c1c"
GREEN = "#047857"
AMBER = "#b45309"
SCENARIO_COLORS = {"ACT": INK, "BUD": "#9ca3af", "FCT": BLUE, "UP": GREEN, "DOWN": RED}
SCENARIO_NAMES = {"ACT": "Actual", "BUD": "Budget", "FCT": "Base forecast", "UP": "Upside", "DOWN": "Downside"}


@st.cache_data
def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PUBLISHED / name)


@st.cache_data
def js(name: str) -> dict:
    return json.loads((PUBLISHED / name).read_text(encoding="utf-8"))


def available() -> bool:
    return (PUBLISHED / "manifest.json").exists()


def require_data():
    if not available():
        st.error("Published data not found. Run `make all` to download sources and build the model.")
        st.stop()


def q_sort_key(label: str) -> int:
    return int(label[:4]) * 4 + int(label[5]) - 1


def financial_wide() -> pd.DataFrame:
    actual = csv("financial_actual.csv")
    derived = csv("financial_derived.csv")
    both = pd.concat([actual[["metric_id", "period_label", "period_type", "period_end", "value"]],
                      derived[["metric_id", "period_label", "period_type", "period_end", "value"]]])
    q = both[both["period_type"] != "FY"]
    wide = q.pivot_table(index=["period_label", "period_end"], columns="metric_id", values="value").reset_index()
    wide["order"] = wide["period_label"].map(q_sort_key)
    return wide.sort_values("order")


def usd_b(x) -> str:
    return "n/a" if pd.isna(x) else f"${x / 1e9:,.2f}B"


def pct(x, digits=1) -> str:
    return "n/a" if pd.isna(x) else f"{x * 100:,.{digits}f}%"


def page_setup(title: str):
    st.set_page_config(page_title=f"{title} | Delta FP&A", layout="wide")
    st.markdown(
        """<style>
        .block-container {padding-top: 2rem; max-width: 1280px;}
        div[data-testid="stMetricValue"] {font-size: 1.6rem;}
        .note {color: #6b7280; font-size: 0.85rem;}
        </style>""",
        unsafe_allow_html=True,
    )


def footnote(text: str):
    st.markdown(f'<p class="note">{text}</p>', unsafe_allow_html=True)
