from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from .models import LogEvent

ALIASES = {
    "timestamp": ("timestamp", "time", "datetime", "date", "event_time"),
    "severity": ("severity", "level", "priority", "status"),
    "asset": ("asset", "device", "machine", "equipment", "source", "component"),
    "code": ("code", "fault_code", "error_code", "alarm", "event_id"),
    "message": ("message", "description", "detail", "text", "event"),
}
SEVERITIES = {"TRACE", "DEBUG", "INFO", "NOTICE", "WARN", "WARNING", "ERROR", "CRITICAL", "FATAL", "ALARM"}
TEXT_PATTERNS = (
    re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ][0-9:.+-]+Z?)\s+\[?(?P<severity>[A-Za-z]+)\]?\s+(?:asset=)?(?P<asset>[\w.-]+)\s+(?:code=)?(?P<code>[\w.-]+)\s+(?P<message>.+)$"),
    re.compile(r"^(?P<timestamp>\d{4}/\d{2}/\d{2}[ T][0-9:.]+)\s*[,|]\s*(?P<severity>[A-Za-z]+)\s*[,|]\s*(?P<asset>[^,|]+)\s*[,|]\s*(?P<code>[^,|]+)\s*[,|]\s*(?P<message>.+)$"),
)


def _value(record: Mapping[str, object], field: str, default: str = "") -> str:
    lowered = {str(k).lower().strip(): v for k, v in record.items()}
    for alias in ALIASES[field]:
        if alias in lowered and lowered[alias] not in (None, ""):
            return str(lowered[alias]).strip()
    return default


def _timestamp(value: str) -> datetime:
    clean = value.strip().replace("Z", "+00:00")
    for parser in (
        lambda: datetime.fromisoformat(clean),
        lambda: datetime.strptime(clean, "%Y/%m/%d %H:%M:%S"),
        lambda: datetime.strptime(clean, "%m/%d/%Y %H:%M:%S"),
    ):
        try:
            parsed = parser()
            return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unsupported timestamp: {value!r}")


def _event(record: Mapping[str, object], source: str, line_number: int) -> LogEvent:
    severity = _value(record, "severity", "INFO").upper()
    severity = "WARN" if severity == "WARNING" else severity
    return LogEvent(
        timestamp=_timestamp(_value(record, "timestamp")),
        severity=severity if severity in SEVERITIES else "INFO",
        asset=_value(record, "asset", "UNKNOWN"),
        code=_value(record, "code", "UNSPECIFIED"),
        message=_value(record, "message", "No message"),
        source=source,
        line_number=line_number,
    )


def parse_text(text: str, source: str = "memory.log") -> tuple[list[LogEvent], list[str]]:
    """Parse log content and return valid events plus human-readable rejected-line messages."""
    events: list[LogEvent] = []
    errors: list[str] = []
    stripped = text.lstrip("\ufeff \r\n\t")
    suffix = Path(source).suffix.lower()

    if suffix == ".csv":
        records = list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
        numbered: Iterable[tuple[int, Mapping[str, object]]] = enumerate(records, start=2)
    elif suffix in {".json", ".jsonl", ".ndjson"} or stripped.startswith(("{", "[")):
        try:
            payload = json.loads(stripped)
            records = payload if isinstance(payload, list) else [payload]
            numbered = enumerate(records, start=1)
        except json.JSONDecodeError:
            numbered = []
            for number, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    numbered.append((number, json.loads(line)))
                except json.JSONDecodeError as exc:
                    errors.append(f"{source}:{number}: invalid JSON ({exc.msg})")
    else:
        numbered = []
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            match = next((pattern.match(line.strip()) for pattern in TEXT_PATTERNS if pattern.match(line.strip())), None)
            if match:
                numbered.append((number, match.groupdict()))
            else:
                errors.append(f"{source}:{number}: unrecognized log format")

    for number, record in numbered:
        try:
            if not isinstance(record, Mapping):
                raise ValueError("record is not an object")
            events.append(_event(record, source, number))
        except (ValueError, TypeError) as exc:
            errors.append(f"{source}:{number}: {exc}")
    return events, errors


def parse_files(paths: Iterable[str | Path]) -> tuple[list[LogEvent], list[str]]:
    events: list[LogEvent] = []
    errors: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        parsed, rejected = parse_text(path.read_text(encoding="utf-8-sig"), path.name)
        events.extend(parsed)
        errors.extend(rejected)
    return sorted(events, key=lambda event: event.timestamp), errors
