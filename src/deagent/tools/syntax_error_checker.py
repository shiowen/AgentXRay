"""Check generated Python files for syntax errors."""

import ast
from typing import List

from deagent.utils import filter_code


def syntax_error_checker(code_content: str):
    """
    Parse generated Python files without executing them.

    Returns False when all parsed files are syntactically valid.
    """

    codebooks = filter_code(code_content)
    if not codebooks:
        return "No code files found to check."

    syntax_errors: List[str] = []
    for filename, content in codebooks.items():
        try:
            ast.parse(content)
        except SyntaxError as exc:
            syntax_errors.append(
                f"File: {filename}, Line: {exc.lineno}, "
                f"Column: {exc.offset}, Error: {exc.msg}"
            )
        except Exception as exc:
            syntax_errors.append(
                f"File: {filename}, An unexpected parsing error occurred: {exc}"
            )

    if not syntax_errors:
        return False
    return "Syntax error check found issues:\n" + "\n".join(syntax_errors)
