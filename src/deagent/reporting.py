"""Reporting helpers used by tests and experiment scripts."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import json
import os
from typing import Any, Dict


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles common runtime objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="ignore")
        if isinstance(obj, Exception):
            return {
                "exception_type": type(obj).__name__,
                "message": str(obj),
                "args": obj.args,
            }
        if callable(obj):
            return f"<callable: {getattr(obj, '__name__', str(obj))}>"
        if hasattr(obj, "__dict__"):
            return {
                str(key): value
                for key, value in vars(obj).items()
                if not str(key).startswith("_")
            }
        return str(obj)


def safe_json_dump(data: Any, file_path: str, indent: int = 2) -> bool:
    """Write JSON safely, returning whether the write succeeded."""

    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, cls=SafeJSONEncoder, indent=indent, ensure_ascii=False)
        return True
    except Exception:
        try:
            with open(file_path + ".backup.txt", "w", encoding="utf-8") as handle:
                handle.write(str(data))
        except Exception:
            pass
        return False


def sanitize_report_data(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert report data into JSON-serializable values."""

    sanitized: Dict[str, Any] = {}
    for key, value in report_data.items():
        if isinstance(value, (datetime, date, time)):
            sanitized[key] = value.isoformat()
        elif key == "execution_time" and isinstance(value, (int, float)):
            sanitized[key] = round(float(value), 3)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_report_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_report_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            try:
                json.dumps(value, cls=SafeJSONEncoder)
                sanitized[key] = value
            except (TypeError, ValueError):
                sanitized[key] = str(value)
    return sanitized
