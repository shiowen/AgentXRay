"""List generated project files as a readable ASCII tree."""

from collections import OrderedDict
from pathlib import PurePosixPath

from deagent.utils import filter_code


def _normalize_filename(filename: str) -> str:
    parts = []
    for part in PurePosixPath(filename.replace("\\", "/")).parts:
        if part in {"", ".", ".."}:
            continue
        parts.append(part)
    return "/".join(parts)


def _build_file_tree(filenames: list[str]) -> dict:
    tree: dict = {}
    for filename in sorted(filter(None, (_normalize_filename(item) for item in filenames))):
        current_level = tree
        parts = filename.split("/")
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                current_level[part] = None
            else:
                current_level = current_level.setdefault(part, {})
    return tree


def _format_tree(tree: dict, prefix: str = "") -> list[str]:
    lines = []
    items = list(OrderedDict(sorted(tree.items())).items())
    for index, (name, content) in enumerate(items):
        is_last = index == len(items) - 1
        connector = "`-- " if is_last else "|-- "
        lines.append(f"{prefix}{connector}{name}")
        if isinstance(content, dict):
            extension = "    " if is_last else "|   "
            lines.extend(_format_tree(content, prefix + extension))
    return lines


def file_lister(code_content: str) -> str:
    """Return a tree-like view of files parsed from a generated project."""

    codebooks = filter_code(code_content)
    if not codebooks:
        return "No files found to list."

    tree_lines = _format_tree(_build_file_tree(list(codebooks.keys())))
    return "Project File Structure:\n.\n" + "\n".join(tree_lines)
