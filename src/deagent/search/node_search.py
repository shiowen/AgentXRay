# search/node_search.py
from deagent.utils import logger
import re
from deagent.agents import GenerateAgent, TaskType, NodeType
import os
import json
from functools import lru_cache
try:
    import yaml
except ImportError:  # pragma: no cover - only used in minimal environments
    yaml = None

def _load_search_config() -> dict:
    if yaml is None:
        return {}
    project_path = os.path.dirname(os.path.dirname(__file__))
    default_cfg = os.path.join(project_path, 'config', 'config.yaml')
    cfg_path = os.environ.get('CONFIG_PATH', default_cfg)
    with open(cfg_path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}

def employee_search(task, child_list, max_num):
    """
    
    
    Args:
        task: 
        child_list: 
        max_num: 
        
    Returns:
        list: agent profile
    """
    ag_agent = GenerateAgent(TaskType.CODE)
    agent_list = []
    employees = ""
    epoch = 0
    curr_num = 0
    
    # agent
    for child in child_list:
        if child.type == NodeType.AGENT:
            employees += child.data
            employees += "\n\n"
            curr_num += 1
    
    try:
        intended_total = max_num if max_num is not None else 1
    except Exception:
        intended_total = 1
    safe_to_generate = max(1, intended_total - curr_num)

    logger.info(f"Starting employee search: current agents = {curr_num}, intended_total = {intended_total}, to_generate = {safe_to_generate}")
    
    while epoch < safe_to_generate:
        logger.info(f"Employee search iteration {epoch + 1}")
        
        #  1:  GenerateAgent 
        try:
            response = ag_agent.query_gpt(task, employees)
        except Exception as e:
            logger.warning(f"GenerateAgent query failed: {e}. Using empty response for fallback agent.")
            response = ""
        
        #  2: 
        selected_model = extract_selected_model(response)
        reasoning_pattern = extract_reasoning_pattern(response)
        # Agent
        pattern = re.compile(r'Name: (.*?)\s+Role: (.*?)\s+Profile: (.*)', re.DOTALL)
        matches = pattern.findall(response)
        
        if matches:
            logger.info("Successfully parsed agent information")
            logger.debug(f"Agent response: {response[:200]}...")
            match_agent = matches[0]
            name, role, profile = match_agent
            
            agent_profile = f'Name:{name}\nRole:{role}\nProfile:{profile}\nModel:{selected_model}\nReasoning:{reasoning_pattern}\n'
            
            agent_list.append(agent_profile)
            employees += agent_profile
            employees += "\n\n"
            epoch += 1
            
            logger.info(f"Added agent {epoch}: {name} ({role})")
        else:
            logger.warning("Failed to parse agent information from response; creating fallback agent.")
            # AgentAgent
            fallback_idx = len(agent_list) + curr_num + 1
            name = f"GeneralistDev{fallback_idx}"
            role = "Code Generator"
            profile = f"Write and refine code for the task: {str(task)[:80]}"
            agent_profile = f'Name:{name}\nRole:{role}\nProfile:{profile}\nModel:{selected_model}\nReasoning:{reasoning_pattern}\n'
            agent_list.append(agent_profile)
            employees += agent_profile + "\n\n"
            epoch += 1
            continue
    
    logger.info(f"Employee search completed: generated {len(agent_list)} agents")
    return agent_list

def _get_default_model() -> str:
    """Fetch the configured default model (falls back to gpt-3.5-turbo)."""
    env_model = os.environ.get('DEAGENT_DEFAULT_MODEL')
    if env_model:
        return env_model
    try:
        cfg = _load_search_config()
        return cfg.get('dynamic_selection', {}).get('fallback', {}).get('default_model', 'gpt-3.5-turbo')
    except Exception:
        return 'gpt-3.5-turbo'

def _get_default_reasoning() -> str:
    """Fetch the configured default reasoning pattern (falls back to reasoning)."""
    try:
        cfg = _load_search_config()
        return cfg.get('dynamic_selection', {}).get('fallback', {}).get('default_reasoning', 'reasoning')
    except Exception:
        return 'reasoning'

def _looks_like_placeholder(value: str) -> bool:
    if not value:
        return True
    v = value.strip().lower()
    return (
        "one of the available" in v
        or "choose exactly" in v
        or "choose one" in v
        or "exact name only" in v
        or v in {"[model_name]", "[pattern_name]", "<model_name>", "<pattern_name>"}
    )

@lru_cache(maxsize=1)
def _get_allowed_models() -> list:
    """Load allowed model names from the configured model_library.json."""
    env_models = [m.strip() for m in os.environ.get('DEAGENT_ALLOWED_MODELS', '').split(',') if m.strip()]
    if env_models:
        return env_models
    try:
        project_path = os.path.dirname(os.path.dirname(__file__))
        cfg = _load_search_config()
        rel_path = (cfg.get('dynamic_selection', {}) or {}).get('model_library_path', 'config/model_library.json')
        model_path = rel_path if os.path.isabs(rel_path) else os.path.join(project_path, rel_path)
        with open(model_path, 'r', encoding='utf-8') as handle:
            library = json.load(handle) or {}
        models = library.get('models', []) or []
        names = [m.get('name') for m in models if isinstance(m, dict) and m.get('name')]
        return names
    except Exception:
        return []

@lru_cache(maxsize=1)
def _get_allowed_reasoning_patterns() -> list:
    """Load allowed reasoning pattern names from configured reasoning_patterns.json."""
    try:
        project_path = os.path.dirname(os.path.dirname(__file__))
        cfg = _load_search_config()
        rel_path = (cfg.get('dynamic_selection', {}) or {}).get('reasoning_patterns_path', 'config/reasoning_patterns.json')
        patterns_path = rel_path if os.path.isabs(rel_path) else os.path.join(project_path, rel_path)
        with open(patterns_path, 'r', encoding='utf-8') as handle:
            patterns_json = json.load(handle) or {}
        patterns = patterns_json.get('patterns', []) or []
        names = [p.get('name') for p in patterns if isinstance(p, dict) and p.get('name')]
        return names
    except Exception:
        return []

def extract_selected_model(response: str) -> str:
    """Extract selected model from GenerateAgent response.

    Accepts common variants:
      - **Selected Model**: xxx
      - Selected Model: xxx
      - Model: xxx
    Cleans wrappers like [xxx], `xxx`, *xxx* and trailing commentary.
    """
    default_model = _get_default_model()
    if not response:
        logger.warning("Empty response when extracting model; using default")
        return default_model

    patterns = [
        r"\*\*Selected Model\*\*\s*:\s*([^\n]+)",
        r"^\s*Selected Model\s*:\s*([^\n]+)",
        r"^\s*Model\s*:\s*([^\n]+)",
    ]

    candidate = None
    for pat in patterns:
        m = re.search(pat, response, re.IGNORECASE | re.MULTILINE)
        if m:
            candidate = m.group(1).strip()
            break

    if not candidate:
        logger.warning("No model selection found in response, using default")
        return default_model

    # Normalize: remove wrappers and extra markup
    candidate = candidate.strip()
    candidate = re.sub(r"^[\s\[\(`\*\"]+", "", candidate)
    candidate = re.sub(r"[\s\]\)`\*\"]+$", "", candidate)
    candidate = candidate.split('|')[0].strip()
    candidate = candidate.split('#')[0].strip()

    if _looks_like_placeholder(candidate):
        logger.warning(f"Parsed placeholder/empty model value '{candidate}'; using default")
        candidate = default_model

    allowed = _get_allowed_models()
    if allowed and candidate not in allowed:
        logger.warning(f"Model '{candidate}' not in allowed list; falling back")
        candidate = default_model if default_model in allowed else allowed[0]

    if not candidate:
        logger.warning("Parsed empty model value after fallback; using default")
        return default_model

    logger.debug(f"Extracted model: {candidate}")
    return candidate

def extract_reasoning_pattern(response: str) -> str:
    """Extract reasoning pattern from GenerateAgent response with tolerant parsing."""
    default_reasoning = _get_default_reasoning()
    if not response:
        logger.warning("Empty response when extracting reasoning; using default")
        return default_reasoning

    # 1) Profile line: Reasoning: xxx
    match_line = re.search(r"^\s*Reasoning\s*:\s*([^\n]+)", response, re.MULTILINE | re.IGNORECASE)
    if match_line:
        reasoning_pattern = match_line.group(1).strip()
        reasoning_pattern = re.sub(r"^[\[]|[\]]$", "", reasoning_pattern)
        reasoning_pattern = reasoning_pattern.split('|')[0].strip()
        logger.debug(f"Extracted reasoning pattern (profile line): {reasoning_pattern}")
        if _looks_like_placeholder(reasoning_pattern):
            reasoning_pattern = default_reasoning
        allowed = _get_allowed_reasoning_patterns()
        if allowed and reasoning_pattern not in allowed:
            reasoning_pattern = default_reasoning if default_reasoning in allowed else allowed[0]
        return reasoning_pattern or default_reasoning

    # 2) Legacy: **Reasoning Pattern**: xxx / Reasoning Pattern: xxx
    match_legacy = re.search(r"\*\*Reasoning Pattern\*\*\s*:\s*([^\n]+)", response, re.IGNORECASE)
    if not match_legacy:
        match_legacy = re.search(r"^\s*Reasoning Pattern\s*:\s*([^\n]+)", response, re.IGNORECASE | re.MULTILINE)
    if match_legacy:
        reasoning_pattern = match_legacy.group(1).strip()
        reasoning_pattern = re.sub(r"[\[\]]", "", reasoning_pattern)
        reasoning_pattern = reasoning_pattern.split('|')[0].strip()
        logger.debug(f"Extracted reasoning pattern (legacy): {reasoning_pattern}")
        if _looks_like_placeholder(reasoning_pattern):
            reasoning_pattern = default_reasoning
        allowed = _get_allowed_reasoning_patterns()
        if allowed and reasoning_pattern not in allowed:
            reasoning_pattern = default_reasoning if default_reasoning in allowed else allowed[0]
        return reasoning_pattern or default_reasoning

    logger.warning("No reasoning pattern found in response, using default")
    allowed = _get_allowed_reasoning_patterns()
    if allowed and default_reasoning not in allowed:
        return allowed[0]
    return default_reasoning
