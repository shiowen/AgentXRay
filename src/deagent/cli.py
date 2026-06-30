"""Command-line interface for AgentXRay experiments."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is part of project requirements.
    yaml = None


@dataclass(frozen=True)
class DatasetSpec:
    directory: str
    train_file: str
    test_file: str


DATASETS = {
    "atoms": DatasetSpec("atoms", "train.json", "test.json"),
    "chatdev": DatasetSpec("chatdev", "train.json", "test.json"),
    "eduagent": DatasetSpec("eduagent", "train.json", "test.json"),
    "gemini": DatasetSpec("gemini", "train.json", "test.json"),
    "gpt": DatasetSpec("gpt", "train.json", "test.json"),
    "maps": DatasetSpec("maps", "train_alpaca.json", "test_alpaca.json"),
    "metagpt": DatasetSpec("metagpt", "train.json", "test.json"),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_repo_path(path: str, repo_root: Path) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else repo_root / resolved


def _make_run_id(dataset: str, provided_run_id: str = "") -> str:
    if provided_run_id:
        raw_run_id = provided_run_id
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_run_id = f"{dataset}_{timestamp}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_run_id).strip("._-") or "run"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an AgentXRay train/test experiment.")
    parser.add_argument(
        "--dataset",
        choices=sorted(DATASETS),
        default="metagpt",
        help="Dataset split to use.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=20,
        help="MCTS search iterations.",
    )
    parser.add_argument(
        "--config",
        default="src/deagent/config/config.yaml",
        help="YAML config path. This is also exported as CONFIG_PATH.",
    )
    parser.add_argument(
        "--data-root",
        default=os.environ.get("AGENTXRAY_DATA_ROOT", "data"),
        help=(
            "Dataset root containing dataset subdirectories. "
            "Defaults to AGENTXRAY_DATA_ROOT or ./data."
        ),
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional output subdirectory name under outputs/<log_dir>/.",
    )
    parser.add_argument(
        "--train-samples",
        type=int,
        default=0,
        help="Optional limit on training samples; 0 uses the full training split.",
    )
    parser.add_argument(
        "--test-samples",
        type=int,
        default=0,
        help="Optional limit on test samples; 0 uses the full test split.",
    )
    return parser


def _validate_inputs(config_path: Path, data_path: Path, spec: DatasetSpec) -> None:
    missing_paths = [
        path for path in (
            config_path,
            data_path / spec.train_file,
            data_path / spec.test_file,
        )
        if not path.exists()
    ]
    if missing_paths:
        missing = "\n".join(f"- {path}" for path in missing_paths)
        raise FileNotFoundError(f"Required experiment file(s) not found:\n{missing}")


def _is_configured_secret(value: str) -> bool:
    return bool(value and value not in {"YOUR_API_KEY_HERE", "${OPENAI_API_KEY}"})


def _validate_backend_credentials(config_path: Path) -> None:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEAGENT_API_KEY")
    if _is_configured_secret(api_key):
        return

    config = {}
    if yaml is not None:
        with open(config_path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
    config_key = (config.get("model") or {}).get("openai_api_key")
    if _is_configured_secret(config_key):
        return

    raise RuntimeError(
        "Missing API key. Set OPENAI_API_KEY/DEAGENT_API_KEY or configure "
        "model.openai_api_key in the selected YAML config."
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.iterations < 0:
        parser.error("--iterations must be >= 0")
    if args.train_samples < 0 or args.test_samples < 0:
        parser.error("--train-samples and --test-samples must be >= 0")

    repo_root = _repo_root()
    config_path = _resolve_repo_path(args.config, repo_root)
    spec = DATASETS[args.dataset]
    data_root = _resolve_repo_path(args.data_root, repo_root)
    data_path = data_root / spec.directory
    _validate_inputs(config_path, data_path, spec)

    os.environ["CONFIG_PATH"] = str(config_path)
    os.environ["RUN_ID"] = _make_run_id(args.dataset, args.run_id)
    try:
        _validate_backend_credentials(config_path)
    except RuntimeError as exc:
        parser.exit(1, f"{parser.prog}: error: {exc}\n")

    from deagent.experiment import ExperimentRunner

    runner = ExperimentRunner(
        data_path=str(data_path),
        train_filename=spec.train_file,
        test_filename=spec.test_file,
        max_train_samples=args.train_samples or None,
        max_test_samples=args.test_samples or None,
    )
    success, result = runner.run_experiment(train_iterations=args.iterations)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if success else 1
