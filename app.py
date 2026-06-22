from __future__ import annotations

import io
import json
import zipfile
from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from log_analyzer.analysis import FAULT_LEVELS, analyze_events, recurring_faults
from log_analyzer.parser import parse_text
from log_analyzer.reporting import render_html

st.set_page_config(page_title="Automation Fault Analyzer", page_icon="⚙️", layout="wide")
st.title("⚙️ Automation Fault Analyzer")
st.caption("Turn PLC, robot, SCADA, and test-station logs into recurring-fault intelligence.")

uploads = st.sidebar.file_uploader("Upload logs", type=["log", "txt", "csv", "json", "jsonl", "ndjson"], accept_multiple_files=True)
threshold = st.sidebar.number_input("Recurring fault threshold", min_value=1, max_value=100, value=2)
texts: list[tuple[str, str]] = []
if uploads:
    texts = [(item.name, item.getvalue().decode("utf-8-sig", errors="replace")) for item in uploads]
else:
    sample = Path(__file__).parent / "sample_data" / "automation.log"
    texts = [(sample.name, sample.read_text(encoding="utf-8"))]
    st.sidebar.info("Showing the bundled sample log. Upload files to replace it.")

events, errors = [], []
for name, content in texts:
    parsed, rejected = parse_text(content, name)
    events.extend(parsed)
    errors.extend(rejected)

if not events:
    st.error("No valid events were found. Check the supported formats in README.md.")
    st.stop()

df = pd.DataFrame([event.to_dict() for event in events])
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
with st.sidebar.expander("Filters", expanded=True):
    available_dates = (df.timestamp.min().date(), df.timestamp.max().date())
    dates = st.date_input("Date range", value=available_dates, min_value=available_dates[0], max_value=available_dates[1])
    severities = st.multiselect("Severity", sorted(df.severity.unique()), default=sorted(df.severity.unique()))
    assets = st.multiselect("Asset", sorted(df.asset.unique()), default=sorted(df.asset.unique()))
    query = st.text_input("Message contains")

filtered = df[df.severity.isin(severities) & df.asset.isin(assets)]
if isinstance(dates, (tuple, list)) and len(dates) == 2:
    filtered = filtered[(filtered.timestamp.dt.date >= dates[0]) & (filtered.timestamp.dt.date <= dates[1])]
if query:
    filtered = filtered[filtered.message.str.contains(query, case=False, na=False)]
visible_event_ids = set(zip(filtered.source, filtered.line_number))
filtered_events = [event for event in events if (event.source, event.line_number) in visible_event_ids]
summary = analyze_events(filtered_events, int(threshold))

cols = st.columns(5)
for column, label, value in zip(cols, ["Events", "Faults", "Fault rate", "Affected assets", "Recurring"], [summary["total_events"], summary["fault_events"], f"{summary['fault_rate_percent']}%", summary["affected_assets"], summary["recurring_faults"]]):
    column.metric(label, value)

fault_df = filtered[filtered.severity.isin(FAULT_LEVELS)].copy()
left, right = st.columns(2)
with left:
    st.subheader("Fault trend")
    if not fault_df.empty:
        interval = max(timedelta(hours=1), (fault_df.timestamp.max() - fault_df.timestamp.min()) / 30)
        trend = fault_df.set_index("timestamp").resample(interval).size().rename("faults").reset_index()
        st.plotly_chart(px.line(trend, x="timestamp", y="faults", markers=True), use_container_width=True)
    else:
        st.info("No faults match the filters.")
with right:
    st.subheader("Faults by asset")
    if not fault_df.empty:
        counts = fault_df.asset.value_counts().rename_axis("asset").reset_index(name="faults")
        st.plotly_chart(px.bar(counts, x="faults", y="asset", orientation="h", color="faults"), use_container_width=True)

st.subheader("Recurring fault signatures")
faults = recurring_faults(filtered_events, int(threshold))
st.dataframe(pd.DataFrame(faults), use_container_width=True, hide_index=True)
st.subheader("Event explorer")
st.dataframe(filtered.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)

export_summary = analyze_events(filtered_events, int(threshold))
archive = io.BytesIO()
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
    bundle.writestr("events.csv", filtered.to_csv(index=False))
    bundle.writestr("recurring_faults.csv", pd.DataFrame(faults).to_csv(index=False))
    bundle.writestr("summary.json", json.dumps(export_summary, indent=2))
    bundle.writestr("report.html", render_html(export_summary))
st.download_button("Download report bundle", archive.getvalue(), "automation-fault-report.zip", "application/zip", type="primary")
if errors:
    with st.expander(f"Rejected lines ({len(errors)})"):
        st.code("\n".join(errors[:200]))
