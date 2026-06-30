import re
import os
import logging
from datetime import datetime
from deagent.utils.log import output_path

logger = logging.getLogger(__name__)

file_path = os.path.dirname(__file__)
project_path = os.path.dirname(file_path)

def extract_filename_from_line(lines):
    """Extract filename hinted in the heading text before a code block.
    Supports patterns like:
    - "### File: foo.py"
    - "File: foo.py"
    - Any token that looks like name.ext (fallback)
    Returns lowercased filename or empty string if not found.
    """
    if not lines:
        return ""
    # Prefer explicit File: marker
    m = re.search(r"(?i)file:\s*([^\s`]+?\.[A-Za-z0-9_]+)", lines)
    if m:
        return m.group(1).strip().lower()
    # Fallback: pick the first token like name.ext
    m2 = re.search(r"([A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)", lines)
    if m2:
        return m2.group(1).strip().lower()
    return ""

def extract_filename_from_code(code):
    """Infer a plausible filename from code when heading lacks one.
    Try class name as module; otherwise return empty string.
    Caller should handle __main__ and final fallback.
    """
    if not code:
        return ""
    file_name = ""
    regex_extract = r"class\s+(\S+?):\n"
    matches_extract = re.finditer(regex_extract, code, re.DOTALL)
    for match_extract in matches_extract:
        file_name = match_extract.group(1)
        break
    if file_name:
        file_name = file_name.lower().split("(")[0] + ".py"
    return file_name

def format_code(code):
    code = "\n".join([line for line in code.split("\n") if len(line.strip()) > 0])
    return code

def filter_code(generated_content:str):
    """Extract code blocks into a {filename: code} dict.
    Robust to headings like '### File: xxx.py' or plain ```python blocks.
    """
    codebooks = {}
    if not generated_content:
        logger.warning("Generated content is empty")
        return {}
    # Primary matcher: capture the line(s) before the code fence as header
    regex = r"([^\n]*?)\n\s*```[^\n]*\n(.*?)\n\s*```"
    matches = list(re.finditer(regex, generated_content, re.DOTALL))
    if not matches:
        return {}

    auto_idx = 1
    for match in matches:
        code = match.group(2)
        if not code:
            continue
        if "CODE" in code:
            continue
        header = match.group(1) or ""
        filename = extract_filename_from_line(header)
        # Heuristics for filename
        if "__main__" in code and not filename:
            filename = "main.py"
        if not filename:
            filename = extract_filename_from_code(code)
        if not filename:
            filename = f"file_{auto_idx}.py"
            auto_idx += 1
        # Avoid overwriting if same filename appears multiple times
        final_name = filename
        suffix = 1
        while final_name in codebooks:
            base, ext = os.path.splitext(filename)
            final_name = f"{base}_{suffix}{ext}"
            suffix += 1
        codebooks[final_name] = format_code(code)
    return codebooks


def codes_to_content(codebooks):
    """Convert a codebooks dict to a single string. If already a string, return as-is."""
    if isinstance(codebooks, str):
        return codebooks
    if not codebooks:
        return ""
    content = ""
    for filename,codes in codebooks.items():
        content += "\n".join([filename, codes])
        content += "\n"
    return content

def save_codes_file(codebooks): 
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{current_time}"
    folder_path = os.path.join(output_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    for file_name, code in codebooks.items():
        safe_name = os.path.normpath(str(file_name).replace("\\", os.sep))
        if os.path.isabs(safe_name) or safe_name == os.pardir or safe_name.startswith(os.pardir + os.sep):
            logger.warning("Skipping unsafe output file path: %s", file_name)
            continue
        temp_file_path = os.path.join(folder_path, safe_name)
        os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
        with open(temp_file_path, "w", encoding="utf-8") as temp_file:
            temp_file.write(code)
