"""Safe workspace-scoped file reader."""

import json
import logging
import os

logger = logging.getLogger(__name__)

WORKSPACE_BASE = os.path.realpath(os.path.abspath("workspace"))


def _is_path_safe(path: str) -> bool:
    """Return whether the path stays inside the configured workspace."""

    absolute_path = os.path.realpath(os.path.abspath(path))
    try:
        return os.path.commonpath([absolute_path, WORKSPACE_BASE]) == WORKSPACE_BASE
    except ValueError:
        return False


def file_reader(json_content: str) -> str:
    """
    Read a UTF-8 file from the workspace.

    Args:
        json_content: JSON string with a required ``filename`` field.
    """

    try:
        data = json.loads(json_content)
        filename = data.get("filename")

        if not filename:
            return "File Reader Error: 'filename' is required."

        full_path = os.path.join(WORKSPACE_BASE, filename)
        if not _is_path_safe(full_path):
            return (
                "File Reader Error: SECURITY VIOLATION - "
                f"Attempted to read from an unsafe path: {filename}"
            )

        if not os.path.exists(full_path):
            return f"File Reader Error: File '{filename}' not found."

        with open(full_path, "r", encoding="utf-8") as handle:
            return handle.read()

    except json.JSONDecodeError:
        return "File Reader Error: Input must be a valid JSON string."
    except Exception as exc:
        logger.exception("file_reader: unexpected error")
        return f"File Reader Error: An unexpected error occurred. Details: {exc}"
