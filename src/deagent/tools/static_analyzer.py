"""Run flake8 static analysis on generated Python code."""

import logging
import os
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)

try:
    import flake8  # noqa: F401
except ImportError:

    def static_analyzer(code_content: str) -> str:
        return (
            "Error: The 'flake8' library is not installed. "
            "Please install it by running: pip install flake8"
        )

else:

    def static_analyzer(code_content: str) -> str:
        """Return flake8 findings for a Python source string."""

        if not code_content or not isinstance(code_content, str) or not code_content.strip():
            return "Static Analyzer Error: Input code is empty."

        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+", delete=False, suffix=".py", encoding="utf-8"
            ) as tmp_file:
                tmp_file.write(code_content)
                tmp_file_path = tmp_file.name

            result = subprocess.run(
                [sys.executable, "-m", "flake8", tmp_file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0 and "invalid syntax" in result.stderr:
                return (
                    "Static Analyzer Error: Syntax error detected. "
                    f"Please use the compiler tool first. Details: {result.stderr}"
                )

            if not result.stdout:
                return "Static analysis passed. No issues found."

            report_lines = result.stdout.strip().splitlines()
            cleaned_report = [
                line.replace(f"{tmp_file_path}:", "line ") for line in report_lines
            ]
            return "Static analysis found issues:\n" + "\n".join(cleaned_report)

        except subprocess.TimeoutExpired:
            return "Static Analyzer Error: Analysis timed out after 30 seconds."
        except Exception as exc:
            logger.exception("static_analyzer: unexpected error")
            return (
                "Static Analyzer Error: An unexpected error occurred. "
                f"Details: {exc}"
            )
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
