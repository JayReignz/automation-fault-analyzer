from log_analyzer.analysis import normalize_message, recurring_faults
from log_analyzer.parser import parse_text


def test_plain_text_parsing_and_rejected_lines():
    events, errors = parse_text("2026-01-01 10:00:00 ERROR PLC-1 E42 Motor 7 failed\nnot valid", "line.log")
    assert len(events) == 1
    assert events[0].asset == "PLC-1"
    assert events[0].code == "E42"
    assert len(errors) == 1


def test_json_aliases_are_supported():
    text = '{"time":"2026-01-01T10:00:00Z","level":"warning","device":"R1","error_code":"W9","description":"Hot"}'
    events, errors = parse_text(text, "event.json")
    assert not errors
    assert events[0].severity == "WARN"
    assert events[0].asset == "R1"


def test_variable_numbers_share_a_signature():
    assert normalize_message("Timeout after 5000 ms") == normalize_message("Timeout after 9000 ms")


def test_recurring_fault_threshold():
    text = "\n".join([
        "2026-01-01 10:00:00 ERROR PLC-1 E42 Motor 7 failed",
        "2026-01-01 10:01:00 ERROR PLC-2 E42 Motor 8 failed",
        "2026-01-01 10:02:00 INFO PLC-2 OK Running",
    ])
    events, _ = parse_text(text)
    faults = recurring_faults(events, threshold=2)
    assert len(faults) == 1
    assert faults[0]["count"] == 2
    assert faults[0]["assets"] == ["PLC-1", "PLC-2"]
