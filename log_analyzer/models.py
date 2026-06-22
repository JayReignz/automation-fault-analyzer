from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LogEvent:
    timestamp: datetime
    severity: str
    asset: str
    code: str
    message: str
    source: str = "unknown"
    line_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.astimezone(timezone.utc).isoformat()
        return data
