COMPILER_PROMPT = '''
This is a tool for checking the execution of the current code. 
Here is the content to be checked:
{content}
Here are the results of the tool's execution:
{result}
If the result is not successful, please correct the code based on the error message.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

'''

EMPTY_DETECT_PROMPT = '''
This tool checks if the code files contain 'pass', '# TODO', and other similar content. It returns a report indicating which functions and lines contain these keywords.
Here is the content to be checked:
{content}
Here are the results of the tool's execution:
{result}
The code should not contain incomplete parts. Please modify the code based on the report.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

'''

VARIABLE_CHECKER_PROMPT = """
This tool checks for variable-related issues in the code, such as undefined names or unused variables/imports.
Here is the content to be checked:
{content}
Here are the results of the tool's execution:
{result}
Please correct the code based on the issues identified in the report to improve code quality and fix potential bugs.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

"""

UNDEFINED_NAME_CHECKER_PROMPT = """
This tool checks for undefined names (variables or functions) in the code.
Here is the content to be checked:
{content}
Here are the results of the tool's execution:
{result}
Please correct the code based on the "undefined name" errors identified in the report.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

"""

SYNTAX_ERROR_CHECKER_PROMPT = """
This tool checks for basic syntax errors in the code without executing it.
Here is the content to be checked:
{content}
Here are the results of the tool's execution:
{result}
Please correct the syntax errors identified in the report.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

"""

STYLE_CHECKER_PROMPT = """
This tool checks the code against the PEP 8 style guide.
Here is the content to be checked:
{content}
Here are the results of the tool's execution:
{result}
Please refactor the code to fix the style violations identified in the report and ensure it conforms to PEP 8.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

"""



DEPENDENCY_EXTRACTOR_PROMPT = """
This tool has scanned the project code and extracted the following third-party library dependencies.
Here is the original code that was checked:
{content}
Here is the list of extracted dependencies:
{result}
Please use this list to generate the content for the `requirements.txt` file.

IMPORTANT OUTPUT FORMAT:
Your output should ONLY be the content of the `requirements.txt` file, wrapped in a markdown code block. For example:
File: requirements.txt
```
requests==2.28.1
numpy==1.23.5
```
Make sure to use ``` markers for proper code extraction.

"""


FILE_LISTER_PROMPT = """
This tool has scanned the project and generated the following file structure.
Here is the original code that was checked:
{content}
Here is the file structure report:
{result}
Please analyze this file structure to understand the project layout before proceeding with your task (e.g., planning, documentation, or refactoring).

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

"""

CODE_SUMMARIZER_PROMPT = """
This tool has analyzed a Python file and generated a summary of its classes and functions.
Here is the original code that was analyzed:
{content}
Here is the summary of the code's structure:
{result}
Please use this summary to understand the module's public API and interfaces before proceeding with your task.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

"""

TEST_RUNNER_PROMPT = """
This tool runs tests on the provided code using pytest and returns the results.
Here is the code that was tested:
{content}
Here is the pytest report:
{result}
If any tests failed, please analyze the failure report and correct the code. If all tests passed, the task is likely complete.

IMPORTANT OUTPUT FORMAT:
Please wrap your Python code in markdown code blocks:

```python
def your_function():
    # Your implementation
    return result
Make sure to use ```python markers for proper code extraction.

"""

FILE_WRITER_PROMPT = """
The file_writer tool was called to save content to the disk.
Original request details:
{content}
Execution result:
{result}
This step is complete. Analyze the result to confirm success and decide the next action.
"""

FILE_READER_PROMPT = """
The file_reader tool was called to read a file from the disk.
The content of the requested file is:
{result}
Please use this content as context for your next action.
"""
