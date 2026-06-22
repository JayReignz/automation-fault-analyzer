from __future__ import annotations

import argparse

from .parser import parse_files
from .reporting import export_reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze automation logs and export fault reports.")
    parser.add_argument("logs", nargs="+", help="Log files in text, CSV, JSON, or JSONL format")
    parser.add_argument("--output", "-o", default="reports", help="Report output directory")
    parser.add_argument("--threshold", "-t", type=int, default=2, help="Minimum occurrences for a recurring fault")
    args = parser.parse_args()
    if args.threshold < 1:
        parser.error("--threshold must be at least 1")
    events, errors = parse_files(args.logs)
    if not events:
        parser.error("no valid log events found")
    paths = export_reports(events, args.output, args.threshold)
    print(f"Parsed {len(events)} events ({len(errors)} rejected lines).")
    for path in paths:
        print(f"Created {path}")
    if errors:
        print("Warnings:")
        for error in errors[:10]:
            print(f"  {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
