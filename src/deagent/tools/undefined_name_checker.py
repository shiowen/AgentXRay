"""Find undefined names in generated Python files."""

from typing import List

from deagent.utils import filter_code

try:
    from pyflakes.api import check as pyflakes_check
    from pyflakes.reporter import Reporter
except ImportError:

    def undefined_name_checker(code_content: str):
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

    def undefined_name_checker(code_content: str):
        """Return only pyflakes messages related to undefined names."""

        codebooks = filter_code(code_content)
        if not codebooks:
            return "No code files found to check."

        all_issues = []
        for filename, content in codebooks.items():
            reporter = _CustomReporter()
            pyflakes_check(content, filename, reporter)
            all_issues.extend(reporter.messages)

        undefined_name_issues = [
            issue for issue in all_issues if "undefined name" in issue
        ]
        if not undefined_name_issues:
            return False
        return "Undefined name check found issues:\n" + "\n".join(undefined_name_issues)
