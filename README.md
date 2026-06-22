# Automation Log Fault Analyzer

A Python application for parsing automation-system logs, grouping recurring faults, exploring reliability trends in an interactive dashboard, and exporting operational reports.

## Features

- Parses JSON Lines, CSV, and common plain-text log formats
- Normalizes changing IDs, addresses, and numbers into stable fault signatures
- Ranks recurring faults by frequency, affected assets, severity, and duration
- Filters by date, severity, asset, and free text in a Streamlit dashboard
- Exports JSON, CSV, and standalone HTML reports
- Includes a command-line workflow and unit tests

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens with `sample_data/automation.log`. Upload one or more files to analyze your own data.

## Command line

```powershell
python -m log_analyzer sample_data/automation.log --output reports --threshold 2
```

This creates `events.csv`, `recurring_faults.csv`, `summary.json`, and `report.html` in the output directory.

Supported text lines include:

```text
2026-06-21 08:14:03 ERROR PLC-07 E204 Motor overload on conveyor 3
2026-06-21T08:15:11Z [WARN] asset=ROBOT-02 code=W105 Axis temperature high
```

CSV/JSON fields are matched from common aliases such as `timestamp`/`time`, `severity`/`level`, `asset`/`device`, `code`/`fault_code`, and `message`/`description`.

## Test

```powershell
pytest
```
