from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Iterable

from .models import LogEvent

FAULT_LEVELS = {"WARN", "ERROR", "CRITICAL", "FATAL", "ALARM"}
SEVERITY_WEIGHT = {"TRACE": 0, "DEBUG": 0, "INFO": 1, "NOTICE": 1, "WARN": 2, "ERROR": 3, "ALARM": 4, "CRITICAL": 4, "FATAL": 5}


def normalize_message(message: str) -> str:
    normalized = message.lower().strip()
    normalized = re.sub(r"\b(?:0x)?[0-9a-f]{6,}\b", "<id>", normalized)
    normalized = re.sub(r"\b\d+(?:\.\d+)?\b", "<n>", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def signature(event: LogEvent) -> str:
    return f"{event.code.upper()} | {normalize_message(event.message)}"


def recurring_faults(events: Iterable[LogEvent], threshold: int = 2) -> list[dict[str, object]]:
    groups: dict[str, list[LogEvent]] = defaultdict(list)
    for event in events:
        if event.severity in FAULT_LEVELS:
            groups[signature(event)].append(event)

    results: list[dict[str, object]] = []
    for fault_signature, occurrences in groups.items():
        if len(occurrences) < threshold:
            continue
        ordered = sorted(occurrences, key=lambda item: item.timestamp)
        highest = max(occurrences, key=lambda item: SEVERITY_WEIGHT.get(item.severity, 0)).severity
        results.append({
            "signature": fault_signature,
            "code": ordered[0].code,
            "example_message": ordered[0].message,
            "count": len(ordered),
            "severity": highest,
            "assets": sorted({item.asset for item in ordered}),
            "first_seen": ordered[0].timestamp.isoformat(),
            "last_seen": ordered[-1].timestamp.isoformat(),
            "span_minutes": round((ordered[-1].timestamp - ordered[0].timestamp).total_seconds() / 60, 1),
        })
    return sorted(results, key=lambda item: (-int(item["count"]), -SEVERITY_WEIGHT.get(str(item["severity"]), 0)))


def analyze_events(events: Iterable[LogEvent], threshold: int = 2) -> dict[str, object]:
    items = list(events)
    faults = [event for event in items if event.severity in FAULT_LEVELS]
    severity_counts = Counter(event.severity for event in items)
    asset_counts = Counter(event.asset for event in faults)
    recurring = recurring_faults(items, threshold)
    timestamps: list[datetime] = [event.timestamp for event in items]
    return {
        "total_events": len(items),
        "fault_events": len(faults),
        "fault_rate_percent": round(100 * len(faults) / len(items), 1) if items else 0.0,
        "affected_assets": len({event.asset for event in faults}),
        "recurring_faults": len(recurring),
        "period_start": min(timestamps).isoformat() if timestamps else None,
        "period_end": max(timestamps).isoformat() if timestamps else None,
        "severity_counts": dict(severity_counts.most_common()),
        "faults_by_asset": dict(asset_counts.most_common()),
        "top_recurring_faults": recurring,
    }
