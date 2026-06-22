"""Automation log parsing and fault-analysis toolkit."""

from .analysis import analyze_events, recurring_faults
from .models import LogEvent
from .parser import parse_files, parse_text

__all__ = ["LogEvent", "parse_text", "parse_files", "analyze_events", "recurring_faults"]
