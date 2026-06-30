"""Run pytest on generated multi-file Python code."""

import logging
import os
import subprocess
import sys
import tempfile

from deagent.utils import filter_code
from deagent.tools.path_utils import safe_join

logger = logging.getLogger(__name__)

try:
    import pytest  # noqa: F401
except ImportError:

    def test_runner(code_content: str) -> str:
        return (
            "Error: The 'pytest' library is not installed. "
            "Please install it by running: pip install pytest"
        )

else:

    def test_runner(code_content: str) -> str:
        """Run pytest against code files parsed from a combined source string."""

        if not code_content or not isinstance(code_content, str) or not code_content.strip():
            return "Test Runner Error: Input code is empty."

        try:
            code_files = filter_code(code_content)
            if not code_files:
                return "Test Runner Error: Could not parse any code files from the input."

            test_files_found = any(
                name.startswith("test_") or name.endswith("_test.py")
                for name in code_files
            )
            if not test_files_found:
                return "Test Runner Info: No test files (e.g., 'test_*.py') found to run."

            with tempfile.TemporaryDirectory() as tmpdirname:
                for filename, content in code_files.items():
                    file_path = safe_join(tmpdirname, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w", encoding="utf-8") as handle:
                        handle.write(content)

                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "--tb=short", "-q", tmpdirname],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                output = result.stdout or result.stderr
                if not output:
                    return (
                        "Pytest ran successfully, but produced no output. "
                        "This might indicate no tests were collected."
                    )

                cleaned_output = output.replace(tmpdirname + os.sep, "")
                return f"Pytest Report:\n---\n{cleaned_output.strip()}"

        except subprocess.TimeoutExpired:
            return "Test Runner Error: Test execution timed out after 60 seconds."
        except Exception as exc:
            logger.exception("test_runner: unexpected error")
            return (
                "Test Runner Error: An unexpected error occurred. "
                f"Details: {exc}"
            )
