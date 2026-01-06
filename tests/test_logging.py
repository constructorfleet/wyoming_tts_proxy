import json
import logging
from io import StringIO
from wyoming_tts_proxy.__main__ import JsonFormatter


def test_json_formatter():
    formatter = JsonFormatter()
    log_record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path",
        lineno=10,
        msg="Test message",
        args=None,
        exc_info=None,
        func="test_func",
    )

    formatted = formatter.format(log_record)
    data = json.loads(formatted)

    assert data["message"] == "Test message"
    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert "timestamp" in data
    assert (
        data["module"] == "test_path"
    )  # LogRecord.module is often basename of pathname
    assert data["func"] == "test_func"


def test_json_formatter_exception():
    formatter = JsonFormatter()
    try:
        raise ValueError("Boom")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    log_record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test_path",
        lineno=10,
        msg="Error message",
        args=None,
        exc_info=exc_info,
        func="test_func",
    )

    formatted = formatter.format(log_record)
    data = json.loads(formatted)

    assert data["message"] == "Error message"
    assert "exception" in data
    assert "ValueError: Boom" in data["exception"]
