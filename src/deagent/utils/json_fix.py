"""Compatibility wrappers for JSON reporting helpers."""

from __future__ import annotations

from typing import Any, Dict

from deagent.reporting import SafeJSONEncoder, safe_json_dump, sanitize_report_data


def safe_json_save(data: Any, file_path: str, indent: int = 2) -> bool:
    """Write JSON data using the shared safe-reporting implementation."""

    return safe_json_dump(data, file_path, indent=indent)


def deep_clean_for_json(obj: Any) -> Any:
    """Convert nested report data into JSON-serializable values."""

    if isinstance(obj, dict):
        return sanitize_report_data(obj)
    return obj


def create_fallback_report(original_data: Any, error_message: str) -> Dict[str, Any]:
    """Create a minimal serialization failure report."""

    return {
        "status": "json_serialization_failed",
        "error": error_message,
        "data_type": type(original_data).__name__,
        "data_summary": str(original_data)[:500],
    }
