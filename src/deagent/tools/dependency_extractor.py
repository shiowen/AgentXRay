# tools/dependency_extractor.py
# A static tool that uses the 'pipreqs' library to scan a multi-file Python
# project and extract its third-party dependencies.
# Required package: pipreqs
# To install: pip install pipreqs

import subprocess
import sys
import tempfile
import os
import logging
from deagent.utils import filter_code
from deagent.tools.path_utils import safe_join

#  logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    #  pipreqs 
    import pipreqs
except ImportError:
    def dependency_extractor(code_content: str) -> str:
        """
        A placeholder function that returns an error message if the required
        'pipreqs' library is not installed.
        """
        return ("Error: The 'pipreqs' library is not installed. "
                "Please install it by running: pip install pipreqs")
else:
    def dependency_extractor(code_content: str) -> str:
        """
        Scans a multi-file Python project and extracts third-party dependencies.

        Args:
            code_content (str): The string containing the multi-file Python project.

        Returns:
            str: A string containing the list of dependencies (like in requirements.txt),
                 a message if no dependencies are found, or an error message.
        """
        codebooks = filter_code(code_content)
        if not codebooks:
            return "No code files found to check."

        logger.info("Running dependency extraction with pipreqs.")

        try:
            with tempfile.TemporaryDirectory() as tmpdirname:
                for filename, content in codebooks.items():
                    # pipreqs 
                    if content.strip():
                        file_path = safe_join(tmpdirname, filename)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                
                #  pipreqs 
                #  --print 
                result = subprocess.run(
                    [sys.executable, '-m', 'pipreqs.pipreqs', '--print', tmpdirname],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.stderr and "SyntaxError" in result.stderr:
                     return f"Dependency Extractor Error: A syntax error in the code prevented analysis. Details: {result.stderr}"

                output = result.stdout.strip()

                if not output:
                    return "No third-party dependencies found."
                else:
                    return "Found dependencies:\n" + output

        except subprocess.TimeoutExpired:
            return "Dependency Extractor Error: Analysis timed out after 60 seconds."
        except Exception as e:
            error_message = f"Dependency Extractor Error: An unexpected error occurred. Details: {str(e)}"
            logger.error(error_message, exc_info=True)
            return error_message
