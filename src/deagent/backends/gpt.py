import os
import traceback
from typing import Dict
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential
from deagent.utils import logger
from deagent.utils import usage_stats

try:
    import yaml
except ImportError:  # pragma: no cover - only used in minimal environments
    yaml = None

file_path = os.path.dirname(__file__)
project_path = os.path.dirname(file_path)

_default_cfg = os.path.join(project_path, 'config', 'config.yaml')
config_path = os.environ.get('CONFIG_PATH', _default_cfg)
if yaml is not None:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

model_config = config.get('model') or {}
API_KEY = (
    os.environ.get("OPENAI_API_KEY")
    or os.environ.get("DEAGENT_API_KEY")
    or model_config.get('openai_api_key')
)
BASE_URL = (
    os.environ.get("OPENAI_BASE_URL")
    or os.environ.get("DEAGENT_BASE_URL")
    or model_config.get('base_url')
)
MAX_RETRY_NUMBER = model_config.get('max_retry_number', 10)

if API_KEY in {"", "YOUR_API_KEY_HERE", "${OPENAI_API_KEY}", None}:
    API_KEY = None
if BASE_URL in {"", "YOUR_BASE_URL_HERE", "${OPENAI_BASE_URL}", None}:
    BASE_URL = None

try:
    _cfg_max_tokens = int(config.get('model', {}).get('max_tokens', 4096))
except Exception:
    _cfg_max_tokens = 4096
try:
    DEFAULT_MAX_TOKENS = int(os.environ.get('MAX_TOKENS', _cfg_max_tokens))
except Exception:
    DEFAULT_MAX_TOKENS = _cfg_max_tokens

_client = None


class BackendConfigurationError(ValueError):
    """Raised when the model backend is not configured for requests."""


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not API_KEY:
        raise BackendConfigurationError(
            "Missing API key. Set OPENAI_API_KEY/DEAGENT_API_KEY or configure "
            "model.openai_api_key in the selected YAML config."
        )
    import openai

    client_kwargs = {"api_key": API_KEY}
    if BASE_URL:
        client_kwargs["base_url"] = BASE_URL
    _client = openai.OpenAI(**client_kwargs)
    return _client

@retry(
    wait=wait_exponential(min=10, max=300),
    stop=stop_after_attempt(MAX_RETRY_NUMBER),
    retry=retry_if_not_exception_type(BackendConfigurationError),
)
def chat_completion_request(messages, model_name, model_config_dict: Dict = None):
    """Request a chat completion through the configured OpenAI-compatible API."""
    if model_config_dict is None:
        model_config_dict = {
            "temperature": 1.0,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }

    # Ensure max_tokens always uses the configured default unless explicitly overridden.
    try:
        model_config_dict.setdefault('max_tokens', DEFAULT_MAX_TOKENS)
    except Exception:
        model_config_dict = {"temperature": 1.0, "max_tokens": DEFAULT_MAX_TOKENS}
    
    try:
        response = _get_client().chat.completions.create(
            messages=messages,
            model=model_name,
            temperature=model_config_dict.get('temperature', 1.0),
            max_tokens=model_config_dict.get('max_tokens', DEFAULT_MAX_TOKENS),
        )
        response_dict = response.model_dump()
        logger.info("**[Proxy_Usage_Info Receive]**\nprompt_tokens: {}\ncompletion_tokens: {}\ntotal_tokens: {}\n".format(
            response_dict["usage"]["prompt_tokens"], 
            response_dict["usage"]["completion_tokens"],
            response_dict["usage"]["total_tokens"]
        ))

        # New: log finish_reason so we can confirm truncation (e.g. 'length').
        try:
            finish_reason = None
            if response_dict.get('choices') and isinstance(response_dict['choices'], list):
                finish_reason = response_dict['choices'][0].get('finish_reason')
            if finish_reason:
                logger.info(f"**[Proxy_Finish_Reason]** finish_reason: {finish_reason}")
        except Exception:
            pass

        try:
            usage_stats.add_usage(
                prompt_tokens=response_dict.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response_dict.get("usage", {}).get("completion_tokens", 0),
            )
        except Exception:
            pass
        
        return response_dict['choices'][0]['message']['content']
            
    except BackendConfigurationError:
        raise
    except Exception as e:
        error_msg = f"Chat completion request failed for model {model_name} via proxy. Exception: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)
