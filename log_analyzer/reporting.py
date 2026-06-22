from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Iterable

from .analysis import analyze_events, recurring_faults
from .models import LogEvent


def _write_csv(path: Path, rows: list[dict[str, object]], headers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "; ".join(value) if isinstance(value, list) else value for key, value in row.items()})


def render_html(summary: dict[str, object]) -> str:
    faults = summary["top_recurring_faults"]
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(fault[key]))}</td>" for key in ("code", "severity", "count", "assets", "example_message", "first_seen", "last_seen")) + "</tr>"
        for fault in faults
    ) or '<tr><td colspan="7">No recurring faults at this threshold.</td></tr>'
    return f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>Automation Fault Report</title>
<style>body{{font:15px system-ui;margin:40px;color:#172033}}.metrics{{display:flex;gap:16px;flex-wrap:wrap}}.card{{padding:18px;background:#f3f6fa;border-radius:10px;min-width:140px}}table{{border-collapse:collapse;width:100%;margin-top:24px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #d9e0e8}}th{{background:#172033;color:white}}</style></head>
<body><h1>Automation Fault Report</h1><div class=\"metrics\"><div class=\"card\"><b>Total events</b><br>{summary['total_events']}</div><div class=\"card\"><b>Fault events</b><br>{summary['fault_events']}</div><div class=\"card\"><b>Fault rate</b><br>{summary['fault_rate_percent']}%</div><div class=\"card\"><b>Recurring faults</b><br>{summary['recurring_faults']}</div></div>
<h2>Recurring faults</h2><table><thead><tr><th>Code</th><th>Severity</th><th>Count</th><th>Assets</th><th>Example</th><th>First seen</th><th>Last seen</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""


def export_reports(events: Iterable[LogEvent], output_dir: str | Path, threshold: int = 2) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    items = list(events)
    summary = analyze_events(items, threshold)
    event_rows = [event.to_dict() for event in items]
    fault_rows = recurring_faults(items, threshold)
    _write_csv(output / "events.csv", event_rows, ["timestamp", "severity", "asset", "code", "message", "source", "line_number"])
    _write_csv(output / "recurring_faults.csv", fault_rows, ["signature", "code", "example_message", "count", "severity", "assets", "first_seen", "last_seen", "span_minutes"])
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "report.html").write_text(render_html(summary), encoding="utf-8")
    return [output / name for name in ("events.csv", "recurring_faults.csv", "summary.json", "report.html")]
