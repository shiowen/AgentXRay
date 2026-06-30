import os
import importlib
from abc import ABC, abstractmethod
from deagent.agents.typing import TaskType
import json
from deagent.utils import logger
from deagent.config.task_prompt import AGPROMPT, EMPLOYEE_PROMPT
from deagent.config.tool_prompt import COMPILER_PROMPT, EMPTY_DETECT_PROMPT, UNDEFINED_NAME_CHECKER_PROMPT, VARIABLE_CHECKER_PROMPT, SYNTAX_ERROR_CHECKER_PROMPT, STYLE_CHECKER_PROMPT, DEPENDENCY_EXTRACTOR_PROMPT, FILE_LISTER_PROMPT, CODE_SUMMARIZER_PROMPT, TEST_RUNNER_PROMPT, FILE_WRITER_PROMPT, FILE_READER_PROMPT
try:
    import yaml
except ImportError:  # pragma: no cover - only used in minimal environments
    yaml = None

file_path = os.path.dirname(__file__)
project_path = os.path.dirname(file_path)
RoleConfig_path = os.path.join(project_path, "config/role_config.json")
TaskConfig_path = os.path.join(project_path, "config/task_config.json")

_default_cfg = os.path.join(project_path, 'config', 'config.yaml')
_cfg_path = os.environ.get('CONFIG_PATH', _default_cfg)
try:
    if yaml is None:
        _cfg = {}
    else:
        with open(_cfg_path, 'r', encoding='utf-8') as handle:
            _cfg = yaml.safe_load(handle) or {}
except Exception:
    _cfg = {}
_model_lib_rel = (_cfg.get('dynamic_selection', {}) or {}).get('model_library_path', 'config/model_library.json')
ModelLibrary_path = _model_lib_rel if os.path.isabs(_model_lib_rel) else os.path.join(project_path, _model_lib_rel)

ReasoningPatterns_path = os.path.join(project_path, "config/reasoning_patterns.json")


def _configured_default_model(fallback: str = "gpt-3.5-turbo") -> str:
    return (
        os.environ.get("DEAGENT_DEFAULT_MODEL")
        or (_cfg.get('dynamic_selection', {}) or {}).get('fallback', {}).get('default_model')
        or fallback
    )


DEFAULT_GENERATION_MODEL = _configured_default_model()


def _allowed_model_filter() -> set:
    raw = os.environ.get("DEAGENT_ALLOWED_MODELS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}

with open(RoleConfig_path, 'r', encoding='utf-8') as file:
    role_config = json.load(file)
with open(TaskConfig_path, "r", encoding="utf-8") as file:
    task_config = json.load(file)


class BaseAgent(ABC):
    def __init__(self, task_type: TaskType, model_name: str):
        super().__init__()
        self.task_type = task_type
        self.model_name = model_name
    
    @abstractmethod
    def get_agent_profile(self) -> str:
        pass

class ToolAgent(BaseAgent):
    TOOL_SPECS = {
        "compiler": ("deagent.tools.compiler", "compiler", COMPILER_PROMPT),
        "empty_detect": ("deagent.tools.empty_detect", "empty_detect", EMPTY_DETECT_PROMPT),
        "variable_checker": ("deagent.tools.variable_checker", "variable_checker", VARIABLE_CHECKER_PROMPT),
        "undefined_name_checker": ("deagent.tools.undefined_name_checker", "undefined_name_checker", UNDEFINED_NAME_CHECKER_PROMPT),
        "syntax_error_checker": ("deagent.tools.syntax_error_checker", "syntax_error_checker", SYNTAX_ERROR_CHECKER_PROMPT),
        "style_checker": ("deagent.tools.style_checker", "style_checker", STYLE_CHECKER_PROMPT),
        "dependency_extractor": ("deagent.tools.dependency_extractor", "dependency_extractor", DEPENDENCY_EXTRACTOR_PROMPT),
        "file_lister": ("deagent.tools.file_lister", "file_lister", FILE_LISTER_PROMPT),
        "code_summarizer": ("deagent.tools.code_summarizer", "code_summarizer", CODE_SUMMARIZER_PROMPT),
        "test_runner": ("deagent.tools.test_runner", "test_runner", TEST_RUNNER_PROMPT),
        "file_writer": ("deagent.tools.file_writer", "file_writer", FILE_WRITER_PROMPT),
        "file_reader": ("deagent.tools.file_reader", "file_reader", FILE_READER_PROMPT),
    }
    FALSEY_NO_EFFECT = {"No code files found to check.", False}

    def __init__(self, task_type, tool_name, model_name = "gpt-3.5-turbo"):
        super().__init__(task_type, model_name)
        self.tool_name = tool_name
    
    def query(self, content):
        spec = self.TOOL_SPECS.get(self.tool_name)
        if spec is None:
            return "Tool not found"

        module_name, function_name, prompt_template = spec
        tool_module = importlib.import_module(module_name)
        tool_function = getattr(tool_module, function_name)
        result = tool_function(content)

        if result in self.FALSEY_NO_EFFECT:
            return False

        if self.tool_name == "file_reader" and "Error:" not in str(result):
            return result

        response = prompt_template.format(content=content, result=result)
        logger.debug(response)
        return response
    
    def get_agent_profile(self):
        return self.tool_name

class EmployeeAgent(BaseAgent):
    def __init__(self, task_type, role_profile, model_name=None):
        super().__init__(task_type, model_name or DEFAULT_GENERATION_MODEL)
        self.role_profile = role_profile
        self.message = ""
        self.code = ""
    
    def query_gpt(self, task: str, content: str) -> str:
        from deagent.backends import chat_completion_request

        prompt = EMPLOYEE_PROMPT.format(task = task, profile = self.role_profile, content = content)
        logger.debug(prompt)
        messages = [{'role': 'system', 'content': ''}, {'role': 'user', 'content': prompt}]
        response = chat_completion_request(messages, model_name = self.model_name)
        logger.debug(response)
        return response

    def get_agent_profile(self):
        return self.role_profile

class GenerateAgent(BaseAgent):
    def __init__(self, task_type, model_name=None):
        super().__init__(task_type, model_name or DEFAULT_GENERATION_MODEL)
        self.role_profile = AGPROMPT
        self.model_library = self._load_model_library()
        self.reasoning_patterns = self._load_reasoning_patterns()
    
    def _load_model_library(self):
        try:
            with open(ModelLibrary_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Failed to load model library: {e}")
            return {
                "models": [
                    {
                        "name": DEFAULT_GENERATION_MODEL,
                        "description": "Default model for general tasks",
                        "token_cost": "medium",
                        "speed": "fast",
                        "best_for": "general programming tasks"
                    }
                ]
            }
    
    def _load_reasoning_patterns(self):
        try:
            with open(ReasoningPatterns_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Failed to load reasoning patterns: {e}")
            return {
                "patterns": [
                    {
                        "name": "reasoning",
                        "description": "Step-by-step logical analysis",
                        "suitable_for": "general problem solving"
                    }
                ]
            }
    
    def _format_model_options(self):
        options = []
        allowed = _allowed_model_filter()
        for model in self.model_library["models"]:
            if allowed and model.get('name') not in allowed:
                continue
            option = f"- {model['name']}: {model['description']} (Cost: {model['token_cost']}, Speed: {model['speed']})"
            options.append(option)
        if not options:
            for model in self.model_library["models"]:
                option = f"- {model['name']}: {model['description']} (Cost: {model['token_cost']}, Speed: {model['speed']})"
                options.append(option)
        return "\n".join(options)
    
    def _format_reasoning_patterns(self):
        patterns = []
        for pattern in self.reasoning_patterns["patterns"]:
            pattern_str = f"- {pattern['name']}: {pattern['description']}"
            patterns.append(pattern_str)
        return "\n".join(patterns)
    
    def query_gpt(self, task: str, employees: str):
        from deagent.backends import chat_completion_request

        model_options = self._format_model_options()
        reasoning_patterns = self._format_reasoning_patterns()
        
        prompt = self.role_profile.format(
            task=task, 
            employees=employees,
            model_options=model_options,
            reasoning_patterns=reasoning_patterns
        )
        logger.debug(prompt)
        messages = [{'role': 'system', 'content': ''}, {'role': 'user', 'content': prompt}]
        response = chat_completion_request(messages, model_name=self.model_name)
        logger.debug(response)
        return response
    
    def get_agent_profile(self):
        return self.role_profile
