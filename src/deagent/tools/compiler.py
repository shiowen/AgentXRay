"""Execute generated Python projects in a temporary workspace."""

import os
import subprocess
import sys
import tempfile

from deagent.utils import filter_code
from deagent.tools.path_utils import safe_join


def compiler(code_content: str) -> str:
    """
    Execute generated code and return a short result message.

    The tool intentionally does not install missing packages at runtime.
    Runtime dependency installation is a repository/environment concern, not
    something an untrusted generated program should trigger.
    """

    codebooks = filter_code(code_content)
    if not codebooks:
        return "No code files found to check."

    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            for filename, content in codebooks.items():
                tmp_file_path = safe_join(tmpdirname, filename)
                os.makedirs(os.path.dirname(tmp_file_path), exist_ok=True)
                with open(tmp_file_path, "w", encoding="utf-8") as handle:
                    handle.write(content)

            main_file_path = os.path.join(tmpdirname, "main.py")
            if not os.path.exists(main_file_path):
                return "Code execution failed: main.py was not generated."

            result = subprocess.run(
                [sys.executable, main_file_path],
                cwd=tmpdirname,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                env={**os.environ, "DISPLAY": ""},
                timeout=30,
            )
            if result.returncode == 0:
                return "Code executed successfully"

            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            details = stderr or stdout or f"process exited with code {result.returncode}"
            return f"Code execution failed: {details}"

        except subprocess.TimeoutExpired:
            return "Code execution timed out. The process was terminated."
        except Exception as exc:
            return f"Code execution failed: {exc}"
