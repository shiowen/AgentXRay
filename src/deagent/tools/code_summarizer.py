"""Summarize Python code structure with the AST module."""

import ast
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _format_args(args_node: ast.arguments) -> str:
    """Format function arguments from an AST node."""

    args = [arg.arg for arg in args_node.args]
    if args_node.vararg:
        args.append(f"*{args_node.vararg.arg}")
    if args_node.kwarg:
        args.append(f"**{args_node.kwarg.arg}")
    return ", ".join(args)


def code_summarizer(code_content: str) -> str:
    """
    Return a concise summary of top-level classes and functions.

    Args:
        code_content: Python source code.
    """

    if not code_content or not isinstance(code_content, str) or not code_content.strip():
        return "Code Summarizer Error: Input code is empty."

    try:
        tree = ast.parse(code_content)
    except SyntaxError as exc:
        logger.warning("Code summarization failed: %s", exc)
        return (
            "Code Summarizer Error: Failed to parse code due to a syntax "
            f"error on line {exc.lineno}. Details: {exc.msg}"
        )

    functions: List[str] = []
    classes: List[Dict[str, Any]] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(f"{node.name}({_format_args(node.args)})")
        elif isinstance(node, ast.ClassDef):
            methods = [
                f"{item.name}({_format_args(item.args)})"
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append({"name": node.name, "methods": methods})

    if not functions and not classes:
        return "Code Summary: No functions or classes found in the provided code."

    summary_lines = ["Code Summary:"]
    if functions:
        summary_lines.append("\nFunctions:")
        summary_lines.extend(f"- {function}" for function in functions)
    if classes:
        summary_lines.append("\nClasses:")
        for cls in classes:
            summary_lines.append(f"- class {cls['name']}:")
            if cls["methods"]:
                summary_lines.extend(f"  - def {method}" for method in cls["methods"])
            else:
                summary_lines.append("  (No methods defined)")

    return "\n".join(summary_lines)
