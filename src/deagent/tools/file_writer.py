"""Safe workspace-scoped file writer."""

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


def file_writer(json_content: str) -> str:
    """
    Write UTF-8 content to a workspace file.

    Args:
        json_content: JSON string with ``filename``, ``content``, optional
            ``overwrite`` and optional ``mode`` fields.
    """

    try:
        data = json.loads(json_content)
        filename = data.get("filename")
        content = data.get("content")
        overwrite = data.get("overwrite", False)
        mode = data.get("mode", "w")

        if not filename or content is None:
            return "File Writer Error: 'filename' and 'content' are required."
        if mode not in {"w", "a"}:
            return f"File Writer Error: Invalid mode '{mode}'. Use 'w' or 'a'."

        full_path = os.path.join(WORKSPACE_BASE, filename)
        if not _is_path_safe(full_path):
            return (
                "File Writer Error: SECURITY VIOLATION - "
                f"Attempted to write to an unsafe path: {filename}"
            )

        if os.path.exists(full_path) and not overwrite and mode == "w":
            return (
                f"File Writer Error: File '{filename}' already exists. "
                "Set overwrite=True to replace it."
            )

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, mode, encoding="utf-8") as handle:
            handle.write(content)

        action = "Appended to" if mode == "a" else "Successfully wrote"
        logger.info("file_writer: %s '%s' (%d chars)", action, full_path, len(content))
        return f"{action} file '{filename}' with {len(content)} characters."

    except json.JSONDecodeError:
        logger.error("file_writer: invalid JSON input")
        return "File Writer Error: Input must be a valid JSON string."
    except Exception as exc:
        logger.exception("file_writer: unexpected error")
        return f"File Writer Error: An unexpected error occurred. Details: {exc}"
