"""Project logging configuration."""

import logging
import os
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - only used in minimal environments
    yaml = None

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "config" / "config.yaml"
CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH))

if yaml is not None and CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
else:
    config = {}

LOG_DIR = (config.get("log") or {}).get("log_dir", "ProjectCodeWithColors")
RUN_ID = os.environ.get("RUN_ID") or os.environ.get("CODE_RUN_NAME") or ""


def _resolve_log_level() -> int:
    level_name = os.environ.get("DEAGENT_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def setup_logger(name: str, log_file: str, level: int = None) -> logging.Logger:
    """Create or update a logger with stream and file handlers."""

    if level is None:
        level = _resolve_log_level()

    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - \n%(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    target_file = os.path.abspath(log_file)
    has_file_handler = any(
        isinstance(handler, logging.FileHandler)
        and os.path.abspath(getattr(handler, "baseFilename", "")) == target_file
        for handler in logger.handlers
    )
    if not has_file_handler:
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    for handler in logger.handlers:
        handler.setLevel(level)

    return logger


output_root = os.environ.get("DEAGENT_OUTPUT_DIR")
if output_root:
    output_path = os.path.join(output_root, LOG_DIR)
else:
    output_path = os.path.join(Path.cwd(), "outputs", LOG_DIR)
if RUN_ID:
    output_path = os.path.join(output_path, RUN_ID)

os.makedirs(output_path, exist_ok=True)

log_file = os.path.join(output_path, "training.log")
logger = setup_logger("global_logger", log_file)
