"""Detect placeholder markers in generated Python files."""

import re
from typing import Dict, List, Optional, Tuple

from deagent.utils import filter_code

Issue = Tuple[int, str, str]


def empty_detect(code_content: str):
    """
    Find placeholder statements and maintenance markers.

    Returns:
        A human-readable report, or a success message when no markers are found.
    """

    codebooks = filter_code(code_content)
    if not codebooks:
        return "No code files found to check."

    patterns = {
        "pass": r"\bpass\b",
        "TODO": r"#\s*TODO",
        "FIXME": r"#\s*FIXME",
        "HACK": r"#\s*HACK",
        "XXX": r"#\s*XXX",
    }
    report: Dict[str, Dict[Optional[str], List[Issue]]] = {}

    for filename, content in codebooks.items():
        current_function: Optional[str] = None
        for line_number, line in enumerate(content.splitlines(), start=1):
            function_match = re.match(r"\s*def\s+(\w+)\s*\(", line)
            if function_match:
                current_function = function_match.group(1)

            for keyword, pattern in patterns.items():
                if re.search(pattern, line):
                    report.setdefault(filename, {}).setdefault(current_function, []).append(
                        (line_number, keyword, line.strip())
                    )

    if not report:
        return "No issues found in the code files."

    lines: List[str] = []
    for filename, functions in report.items():
        lines.append(f"File '{filename}' contains placeholders:")
        for function_name, issues in functions.items():
            scope = function_name or "<module>"
            lines.append(f"  Scope '{scope}':")
            for line_number, keyword, source_line in issues:
                lines.append(f"    Line {line_number}: {keyword} - {source_line}")

    return "\n".join(lines)
