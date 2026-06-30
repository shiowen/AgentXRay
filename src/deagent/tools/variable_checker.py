"""Run pyflakes variable checks on generated Python files."""

from typing import List

from deagent.utils import filter_code

try:
    from pyflakes.api import check as pyflakes_check
    from pyflakes.reporter import Reporter
except ImportError:

    def variable_checker(code_content: str):
        return (
            "Error: The 'pyflakes' library is not installed. "
            "Please install it by running: pip install pyflakes"
        )

else:

    class _CustomReporter(Reporter):
        def __init__(self):
            self.messages: List[str] = []

        def flake(self, message):
            self.messages.append(str(message))

        def unexpectedError(self, filename, msg):
            self.messages.append(f"Unexpected error in {filename}: {msg}")

    def variable_checker(code_content: str):
        """Return pyflakes findings for parsed generated Python files."""

        codebooks = filter_code(code_content)
        if not codebooks:
            return "No code files found to check."

        all_issues = []
        for filename, content in codebooks.items():
            reporter = _CustomReporter()
            pyflakes_check(content, filename, reporter)
            all_issues.extend(reporter.messages)

        if not all_issues:
            return False
        return "Variable check found issues:\n" + "\n".join(all_issues)
