"""Configuration loader for tests and lightweight scripts."""

from pathlib import Path
import os

try:
    import yaml
except ImportError:  # pragma: no cover - only used in minimal environments
    yaml = None


_DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")
_CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", _DEFAULT_CONFIG))

if yaml is not None:
    with _CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
else:
    config = {
        "model": {"openai_api_key": "", "max_retry_number": 10},
        "mcts_tree": {"max_child_number": 16, "max_depth": 6},
        "log": {"log_dir": "ProjectCodeWithColors"},
    }
