"""Run pycodestyle checks on generated multi-file Python code."""

import logging
import os
import subprocess
import sys
import tempfile

from deagent.utils import filter_code
from deagent.tools.path_utils import safe_join

logger = logging.getLogger(__name__)

try:
    import pycodestyle  # noqa: F401
except ImportError:

    def style_checker(code_content: str):
        return (
            "Error: The 'pycodestyle' library is not installed. "
            "Please install it by running: pip install pycodestyle"
        )

else:

    def style_checker(code_content: str):
        """
        Check Python files against PEP 8.

        Returns False when no style violations are found.
        """

        codebooks = filter_code(code_content)
        if not codebooks:
            return "No code files found to check."

        try:
            with tempfile.TemporaryDirectory() as tmpdirname:
                for filename, content in codebooks.items():
                    file_path = safe_join(tmpdirname, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w", encoding="utf-8") as handle:
                        handle.write(content)

                result = subprocess.run(
                    [sys.executable, "-m", "pycodestyle", tmpdirname],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if not result.stdout:
                    return False

                report_lines = result.stdout.strip().splitlines()
                cleaned_report = [
                    line.replace(tmpdirname + os.sep, "") for line in report_lines
                ]
                return "Style check found issues:\n" + "\n".join(cleaned_report)

        except subprocess.TimeoutExpired:
            return "Style Checker Error: Analysis timed out after 30 seconds."
        except Exception as exc:
            logger.exception("style_checker: unexpected error")
            return (
                "Style Checker Error: An unexpected error occurred. "
                f"Details: {exc}"
            )
