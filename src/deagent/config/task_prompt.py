# config/TaskPrompt.py - 

AGPROMPT = '''
Task: {task}

We recruit exactly ONE new employee.
Already hired employees (for diversity reference):
{employees}

Available Models (choose one by exact name):
{model_options}

Available Reasoning Patterns (choose one by exact name):
{reasoning_patterns}

#AGENT SECTION
Provide ONLY the profile fields:
Name:
Role:
Profile: concise skills relevant to the task (avoid fluff). If planning to use any tool just say: Will use <tool_name> when needed.
Work output: code or non-code (choose one).
Model: choose exactly ONE model name from the "Available Models" list above. Output ONLY the exact model name (no extra words).
Reasoning: choose exactly ONE pattern name from the "Available Reasoning Patterns" list above. Output ONLY the exact pattern name (no extra words).

INTERNAL SEARCH STEP RULE:
If this is an internal exploration step (not final code emission), OUTPUT ONLY the above profile section and DO NOT output any files.

FINAL CODE EMISSION RULE (only when explicitly required by controller):
When a step explicitly requires code files, output the MINIMAL runnable skeleton ONLY:
Mandatory files (re-emitted fully each time code is requested):
- main.py
- requirements.txt
No other files unless absolutely necessary for import correctness.

FILE OUTPUT FORMAT (when emitting code):
For each file:
File: real_filename.py
```python
# full file content
```
Never use placeholders like <filename> or [model_name]. No extra prose outside required fields.
'''

EMPLOYEE_PROMPT = '''
You are an employee at the company for software development.
Your personal profile is:
{profile}

The task is: {task}
The content provided to you by the previous roles is:
{content}

You need to complete your work based on the task and the content provided by the previous roles.
If your work output is code, you must follow ALL rules:
- The code must be in Python.
- ABSOLUTE OUTPUT START RULE: Your very first characters MUST be exactly:
  File: main.py
  (No title, no greeting, no explanation, no blank line before it.)
- ZERO-SCORE WARNING: If you output ANY extra text ("preamble", analysis, comments outside code fences) before the first "File:" header, the evaluator will treat it as formatting failure and your score will be zero.
- First list the core classes/functions/methods and their purpose as comments in the main file.
- Then output every file as: ONE heading line immediately followed by ONE python code fence.
  - Heading format (exact, OUTSIDE the fence): File: actual_filename.py
  - The next line MUST start with ```python (no blank line in between)
  - Exactly ONE code block per file. Do NOT nest or repeat fences.
  - IMPORTANT: Do NOT write '# File: ...' inside code blocks. File headers must be outside fences.
  - Do NOT include any line containing the word CODE inside code blocks.
  - Do NOT include any additional prose anywhere outside code blocks.
- Start with the main entry file, then dependencies.
- Ensure the code is fully runnable. Implement all functions; no placeholders like 'pass'.
- Re-output the FULL content of ALL project files every time (complete set), even if unchanged.

OUTPUT LENGTH BUDGET (CRITICAL)
You MUST keep the entire answer within ~7000 tokens.

FORMAT EXAMPLE (VALID):
File: main.py
```python
# ...python code...
```
File: utils.py
```python
# ...python code...
```

'''
