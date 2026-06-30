"""Path helpers for tools that materialize generated files."""

import os


def safe_join(base_dir: str, filename: str) -> str:
    """Join a generated filename to a base directory without allowing escape."""

    target = os.path.realpath(os.path.join(base_dir, filename))
    base = os.path.realpath(base_dir)
    if os.path.commonpath([target, base]) != base:
        raise ValueError(f"Unsafe generated filename: {filename}")
    return target
