try:
    import tiktoken
except ImportError:  # pragma: no cover - only used in minimal environments
    tiktoken = None
import logging

try:
    import regex as re
    _HAS_REGEX = True
except ImportError:  # pragma: no cover - only used in minimal environments
    import re
    _HAS_REGEX = False
import json

logger = logging.getLogger(__name__)

def num_max_token_calc(messages, model_name):
    string = "\n".join([message["content"] for message in messages])
    if tiktoken is not None:
        try:
            encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        num_prompt_tokens = len(encoding.encode(string))
    else:
        num_prompt_tokens = max(1, len(string) // 4)
    gap_between_send_receive = 15 * len(messages)
    num_prompt_tokens += gap_between_send_receive

    num_max_token_map = {
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-3.5-turbo-0613": 4096,
        "gpt-3.5-turbo-16k-0613": 16384,
        "gpt-4": 8192,
        "gpt-4-0125-preview": 128000,
        "gpt-4-turbo": 128000,
        "claude-3-sonnet-20240229": 200000,
        "gpt-4o-mini": 128000
    }

    num_max_token = num_max_token_map.get(model_name, 128000)
    num_max_completion_tokens = num_max_token - num_prompt_tokens

    # If you have special handling for some large-context models
    if model_name in {"gpt-4", "gpt-4-turbo", "gpt-4o-mini"}:
        num_max_completion_tokens = min(num_max_completion_tokens, 4096)
    return max(256, num_max_completion_tokens)

def filter_reviewer_answer(generated_content: str) -> int:
    if generated_content == "":
        logger.warning("Generated reviewer content is empty")
        return None
    else:
        # answer:?
        # regex = r'(?i)\banswer\b:\s*(\d+)'
        # answer:? and answer is ?
        regex = r'(?i)\banswer\b\s*(?:is|:)\s*(-?\d+)'
        matches = re.findall(regex, generated_content)
        if len(matches) == 0:
            answer = 0
        else:
            answer = matches[-1]
    return int(answer)

def filter_strings(content, start_tag, end_tag):
    regex = fr'{start_tag}(.*?){end_tag}'
    matches = re.findall(regex, content, re.DOTALL)
    if len(matches) == 0:
        return ""
    else:
        return matches[-1]
    
def filter_json(content):
    if not _HAS_REGEX:
        decoder = json.JSONDecoder()
        for index, char in enumerate(content):
            if char != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(content[index:])
                return obj
            except json.JSONDecodeError:
                continue
        return ""
    regex = r'\{(?:[^{}]|(?R))*\}'
    json_pattern = re.compile(regex)
    json_matches = json_pattern.findall(content)
    #  JSON 
    valid_jsons = []
    for match in json_matches:
        try:
            json_obj = json.loads(match)
            valid_jsons.append(json_obj)
        except json.JSONDecodeError:
            continue
    if len(valid_jsons) == 0:
        return ""
    else:
        return valid_jsons[0]

def save_result_json(data, file_path: str, mode: str = 'w'):
    with open(file_path, mode, encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# === JSON ===
from .json_fix import safe_json_save

def save_result_json_safe(data, file_path: str, mode: str = 'w'):
    """JSON"""
    return safe_json_save(data, file_path)
