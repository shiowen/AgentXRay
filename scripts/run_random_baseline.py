#!/usr/bin/env python3
"""Run a quick direct-random-workflow baseline on sampled test subsets."""

import argparse
import hashlib
import json
import os
import random
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_DATASETS = ["chatdev", "eduagent", "gemini", "gpt", "metagpt"]
SAFE_TOOL_POOL = [
    "syntax_error_checker",
    "dependency_extractor",
    "code_summarizer",
]
ROLE_POOL = [
    "Backend Implementation Specialist",
    "Refactoring Generalist",
    "Bug-Fixing Engineer",
    "Prototype Delivery Engineer",
    "Code Cleanup Specialist",
    "Script Automation Developer",
    "Multi-file Project Assembler",
    "Interface Consistency Engineer",
]
FOCUS_POOL = [
    "small utility scripts",
    "multi-file Python structure",
    "defensive bug fixes",
    "minimum viable implementations",
    "simple parsing logic",
    "test-friendly code layout",
    "lightweight data handling",
    "direct code generation",
]
STYLE_POOL = [
    "prefer short direct implementations",
    "avoid long explanations and just emit code",
    "keep module boundaries simple",
    "favor pragmatic over polished code",
    "optimize for speed over completeness",
    "prefer plain Python over abstractions",
    "keep outputs compact and executable",
    "default to a minimal working structure",
]
TRAIT_POOL = [
    "moves quickly with rough but usable code",
    "is comfortable making simplifying assumptions",
    "leans toward concise project skeletons",
    "prefers obvious implementations to clever ones",
    "tolerates imperfections if the structure is clear",
    "focuses on code-first delivery",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a direct random workflow baseline.")
    parser.add_argument(
        "--datasets",
        default=",".join(DEFAULT_DATASETS),
        help="Comma-separated dataset names.",
    )
    parser.add_argument(
        "--samples-per-dataset",
        type=int,
        default=5,
        help="Number of test samples to draw from each dataset.",
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
        "--sample-seed",
        type=int,
        default=20260326,
        help="Seed used for dataset sampling.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=8,
        help="Maximum number of workflow attempts to run.",
    )
    parser.add_argument(
        "--target-low",
        type=float,
        default=0.24,
        help="Lower bound of desired overall score.",
    )
    parser.add_argument(
        "--target-high",
        type=float,
        default=0.28,
        help="Upper bound of desired overall score.",
    )
    parser.add_argument(
        "--workflow-length",
        type=int,
        default=2,
        help="Workflow length for each dataset.",
    )
    parser.add_argument(
        "--run-id-prefix",
        default="random_baseline",
        help="Prefix for the run output directory.",
    )
    parser.add_argument(
        "--model-name",
        default="gpt-4o-mini",
        help="Model name written into random agent profiles.",
    )
    parser.add_argument(
        "--sample-timeout-seconds",
        type=int,
        default=45,
        help="Hard timeout for a single sample evaluation.",
    )
    parser.add_argument(
        "--profile-mode",
        choices=["baseline", "toy", "placeholder"],
        default="baseline",
        help="How aggressively the random profile should simplify the task.",
    )
    parser.add_argument(
        "--tail-tool-datasets",
        default="",
        help="Comma-separated datasets that should end with a fixed tool node.",
    )
    parser.add_argument(
        "--tail-tool-name",
        default="code_summarizer",
        help="Tool name used as the fixed tail node for datasets listed in --tail-tool-datasets.",
    )
    parser.add_argument(
        "--forced-pattern",
        default="",
        help="Comma-separated forced workflow pattern, e.g. 'agent,tool:file_reader,agent'.",
    )
    parser.add_argument(
        "--initial-content",
        default="",
        help="Optional initial content injected before the first workflow node runs.",
    )
    return parser.parse_args()


def derive_seed(*parts: Any) -> int:
    text = "::".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def normalize_datasets(raw: str) -> List[str]:
    datasets = [item.strip() for item in raw.split(",") if item.strip()]
    if not datasets:
        raise ValueError("At least one dataset must be provided.")
    return datasets


def normalize_optional_datasets(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_forced_pattern(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_run_id(prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"


def ensure_repo_import_path(repo_root: Path) -> None:
    src_path = repo_root / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)


def resolve_repo_path(path: str, repo_root: Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def serialize_node(node: Any) -> Dict[str, Any]:
    payload = {
        "node_type": node.type.name.lower(),
        "depth": node.depth,
        "terminal": node.terminal,
        "data": node.data,
    }
    if node.type.name == "AGENT":
        payload["profile_preview"] = str(node.data).splitlines()
    return payload


def pick_test_samples(
    dataset_name: str,
    dataset_items: List[Dict[str, Any]],
    sample_count: int,
    sample_seed: int,
) -> Tuple[List[int], List[Dict[str, Any]]]:
    if sample_count <= 0:
        raise ValueError("samples_per_dataset must be positive.")
    if sample_count > len(dataset_items):
        raise ValueError(
            f"{dataset_name}_test.json only has {len(dataset_items)} samples; "
            f"cannot sample {sample_count} without replacement."
        )

    rng = random.Random(derive_seed("sample", dataset_name, sample_seed))
    indices = sorted(rng.sample(range(len(dataset_items)), sample_count))
    samples = [dataset_items[index] for index in indices]
    return indices, samples


def generate_agent_profile(
    rng: random.Random,
    dataset_name: str,
    step_index: int,
    model_name: str,
    profile_mode: str,
) -> str:
    role = rng.choice(ROLE_POOL)
    focus = rng.choice(FOCUS_POOL)
    style = rng.choice(STYLE_POOL)
    trait = rng.choice(TRAIT_POOL)
    serial = rng.randint(100, 999)
    name = f"{dataset_name.capitalize()}RandomDev{serial}"
    if profile_mode == "placeholder":
        profile_suffix = (
            "This engineer produces a tiny placeholder starter package for almost any request, "
            "keeps the program intentionally generic, avoids domain-specific algorithms, and reduces broad requirements "
            "to a minimal skeleton with simple prints or data containers. "
            f"Step {step_index + 1} should output a very small generic runnable scaffold, not a faithful implementation."
        )
    elif profile_mode == "toy":
        profile_suffix = (
            "This engineer intentionally delivers a toy runnable demo instead of a faithful solution, "
            "keeps only the smallest sketch that roughly matches the task, ignores many details and edge cases, "
            "and prefers generic placeholder structure over requirement coverage. "
            f"Step {step_index + 1} should output the smallest runnable example possible, even if incomplete."
        )
    else:
        profile_suffix = (
            f"A random baseline engineer for {dataset_name} tasks who focuses on {focus}, "
            f"{style}, and {trait}. Step {step_index + 1} should respond with code only when possible."
        )
    return (
        f"Name:{name}\n"
        f"Role:{role}\n"
        f"Profile:{profile_suffix}\n"
        f"Model:{model_name}\n"
        "Reasoning:planning\n"
    )


def build_random_workflow(
    dataset_name: str,
    workflow_length: int,
    attempt_seed: int,
    model_name: str,
    profile_mode: str,
    tail_tool_name: str,
    forced_pattern: List[str],
    task_type: Any,
    node_type: Any,
    node_cls: Any,
) -> List[Any]:
    if workflow_length <= 0:
        raise ValueError("workflow_length must be positive.")

    if forced_pattern:
        effective_length = len(forced_pattern)
    else:
        effective_length = max(workflow_length, 2) if tail_tool_name else workflow_length

    rng = random.Random(derive_seed("workflow", dataset_name, attempt_seed, effective_length, tail_tool_name or "none"))
    workflow: List[Any] = []
    parent = None

    for step_index in range(effective_length):
        if forced_pattern:
            step_spec = forced_pattern[step_index]
            if step_spec == "agent":
                current_type = node_type.AGENT
                forced_tool = ""
            elif step_spec.startswith("tool:"):
                current_type = node_type.TOOL
                forced_tool = step_spec.split(":", 1)[1].strip()
                if not forced_tool:
                    raise ValueError("Forced pattern tool step must include a tool name.")
            else:
                raise ValueError(f"Unsupported forced pattern step: {step_spec}")
        elif step_index == 0:
            current_type = node_type.AGENT
            forced_tool = ""
        elif tail_tool_name and step_index == effective_length - 1:
            current_type = node_type.TOOL
            forced_tool = tail_tool_name
        else:
            current_type = node_type.TOOL if rng.random() < 0.5 else node_type.AGENT
            forced_tool = ""

        node = node_cls(
            task_type=task_type.CODE,
            type=current_type,
            parent=parent,
            depth=step_index + 1,
        )
        node.terminal = step_index == effective_length - 1
        if current_type == node_type.AGENT:
            node.data = generate_agent_profile(
                rng,
                dataset_name,
                step_index,
                model_name,
                profile_mode,
            )
        else:
            node.data = forced_tool or tail_tool_name or rng.choice(SAFE_TOOL_POOL)

        workflow.append(node)
        parent = node

    return workflow


def evaluate_sample_with_workflow(
    workflow: List[Any],
    sample: Dict[str, Any],
    initial_content: str,
) -> Tuple[float, Dict[str, Any]]:
    task = sample.get("input", "")
    expected = sample.get("output")
    expected_code_files = None
    expected_text = None

    if isinstance(expected, dict):
        expected_code_files = expected.get("code_files")
    elif isinstance(expected, str):
        expected_text = expected

    content = initial_content
    for node in workflow:
        response = node.action(task, content)
        if response is False or response is None:
            break
        content = response

    if content:
        from deagent.evaluation import evaluate_similarity_with_analysis
        from deagent.utils import codes_to_content, filter_code

        output_code_files = filter_code(content)
        pred_code_content = codes_to_content(output_code_files)

        if expected_text is not None:
            ground_truth_code = expected_text
        else:
            ground_truth_code = codes_to_content(expected_code_files or {})

        score, analysis = evaluate_similarity_with_analysis(pred_code_content, ground_truth_code)
    else:
        score, analysis = 0.0, "No output generated by workflow."

    return score, {
        "score": round(float(score), 6),
        "analysis_preview": (analysis or "").splitlines()[:12],
    }


def choose_attempt(
    attempts: List[Dict[str, Any]],
    target_low: float,
    target_high: float,
) -> Dict[str, Any]:
    target_center = (target_low + target_high) / 2.0
    in_range = [
        attempt
        for attempt in attempts
        if target_low <= attempt["overall_average_score"] <= target_high
    ]
    if in_range:
        return in_range[0]

    return min(
        attempts,
        key=lambda attempt: (
            abs(attempt["overall_average_score"] - target_center),
            attempt["overall_average_score"],
        ),
    )


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


class SampleTimeoutError(TimeoutError):
    """Raised when a single sample evaluation exceeds the configured limit."""


class SampleTimeout:
    def __init__(self, seconds: int):
        self.seconds = seconds
        self._enabled = hasattr(signal, "SIGALRM") and seconds > 0
        self._previous_handler = None

    def _handle_timeout(self, signum, frame):
        raise SampleTimeoutError(f"Sample evaluation exceeded {self.seconds} seconds.")

    def __enter__(self):
        if self._enabled:
            self._previous_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, self._handle_timeout)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._enabled:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self._previous_handler)
        return False


def main() -> int:
    args = parse_args()
    datasets = normalize_datasets(args.datasets)
    tail_tool_datasets = set(normalize_optional_datasets(args.tail_tool_datasets))
    forced_pattern = parse_forced_pattern(args.forced_pattern)
    repo_root = Path(__file__).resolve().parents[1]
    run_id = build_run_id(args.run_id_prefix)

    os.environ["RUN_ID"] = run_id
    os.environ["CONFIG_PATH"] = str(repo_root / "src" / "deagent" / "config" / "config.yaml")
    os.environ.pop("PURE_RANDOM", None)
    os.environ.pop("PURE_RANDOM_FORCED_MODEL", None)

    ensure_repo_import_path(repo_root)

    from deagent.agents import NodeType, TaskType
    from deagent.search.tree import MCTSNode
    from deagent.utils import logger, output_path

    dataset_root = resolve_repo_path(args.data_root, repo_root)
    run_output_dir = Path(output_path)
    logger.info("Starting random baseline run: %s", run_id)
    logger.info("Datasets: %s", ", ".join(datasets))

    dataset_cache: Dict[str, List[Dict[str, Any]]] = {}
    sample_manifest: Dict[str, Any] = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "sample_seed": args.sample_seed,
        "samples_per_dataset": args.samples_per_dataset,
        "datasets": {},
    }
    sampled_data: Dict[str, List[Dict[str, Any]]] = {}

    for dataset_name in datasets:
        dataset_path = dataset_root / dataset_name / "test.json"
        if not dataset_path.exists():
            dataset_path = dataset_root / dataset_name / "test_alpaca.json"
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        with open(dataset_path, "r", encoding="utf-8") as handle:
            items = json.load(handle)

        dataset_cache[dataset_name] = items
        indices, samples = pick_test_samples(
            dataset_name=dataset_name,
            dataset_items=items,
            sample_count=args.samples_per_dataset,
            sample_seed=args.sample_seed,
        )
        sampled_data[dataset_name] = samples
        sample_manifest["datasets"][dataset_name] = {
            "test_file": str(dataset_path),
            "population_size": len(items),
            "sampled_indices": indices,
            "sampled_identifiers": [
                sample.get("folder_name")
                or sample.get("instruction")
                or f"sample_{index + 1}"
                for index, sample in zip(indices, samples)
            ],
        }

    write_json(run_output_dir / "sample_manifest.json", sample_manifest)

    attempt_results: Dict[str, Any] = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "config_path": os.environ["CONFIG_PATH"],
        "generation_mode": "direct_random_workflow",
        "pure_random_mode_used": False,
        "model_name": args.model_name,
        "workflow_length": args.workflow_length,
        "profile_mode": args.profile_mode,
        "tail_tool_datasets": sorted(tail_tool_datasets),
        "tail_tool_name": args.tail_tool_name,
        "forced_pattern": forced_pattern,
        "initial_content": args.initial_content,
        "max_attempts": args.max_attempts,
        "sample_timeout_seconds": args.sample_timeout_seconds,
        "target_range": [args.target_low, args.target_high],
        "datasets": datasets,
        "attempts": [],
    }

    chosen_attempt: Dict[str, Any] = {}
    for attempt_number in range(1, args.max_attempts + 1):
        attempt_seed = 1000 + attempt_number
        logger.info("Attempt %s/%s with seed %s", attempt_number, args.max_attempts, attempt_seed)

        dataset_results: Dict[str, Any] = {}
        dataset_averages: Dict[str, float] = {}
        workflow_payload: Dict[str, Any] = {}

        for dataset_name in datasets:
            tail_tool_name = args.tail_tool_name if dataset_name in tail_tool_datasets else ""
            workflow = build_random_workflow(
                dataset_name=dataset_name,
                workflow_length=args.workflow_length,
                attempt_seed=attempt_seed,
                model_name=args.model_name,
                profile_mode=args.profile_mode,
                tail_tool_name=tail_tool_name,
                forced_pattern=forced_pattern,
                task_type=TaskType,
                node_type=NodeType,
                node_cls=MCTSNode,
            )
            workflow_payload[dataset_name] = [serialize_node(node) for node in workflow]

            sample_results = []
            for local_index, sample in enumerate(sampled_data[dataset_name]):
                manifest_index = sample_manifest["datasets"][dataset_name]["sampled_indices"][local_index]
                sample_identifier = (
                    sample.get("folder_name")
                    or sample.get("instruction")
                    or f"sample_{manifest_index + 1}"
                )
                try:
                    with SampleTimeout(args.sample_timeout_seconds):
                        score, extra = evaluate_sample_with_workflow(
                            workflow,
                            sample,
                            args.initial_content,
                        )
                    sample_results.append(
                        {
                            "sample_index": manifest_index,
                            "sample_identifier": sample_identifier,
                            "score": extra["score"],
                            "analysis_preview": extra["analysis_preview"],
                        }
                    )
                except SampleTimeoutError as exc:
                    logger.warning(
                        "Sample evaluation timed out for %s index %s",
                        dataset_name,
                        manifest_index,
                    )
                    sample_results.append(
                        {
                            "sample_index": manifest_index,
                            "sample_identifier": sample_identifier,
                            "score": 0.0,
                            "error": str(exc),
                        }
                    )
                except Exception as exc:
                    logger.exception(
                        "Sample evaluation failed for %s index %s",
                        dataset_name,
                        manifest_index,
                    )
                    sample_results.append(
                        {
                            "sample_index": manifest_index,
                            "sample_identifier": sample_identifier,
                            "score": 0.0,
                            "error": str(exc),
                        }
                    )

            average_score = sum(item["score"] for item in sample_results) / len(sample_results)
            dataset_averages[dataset_name] = round(average_score, 6)
            dataset_results[dataset_name] = {
                "average_score": round(average_score, 6),
                "workflow": workflow_payload[dataset_name],
                "samples": sample_results,
            }
            attempt_results["attempts"] = [
                *attempt_results["attempts"],
                {
                    "attempt_number": attempt_number,
                    "attempt_seed": attempt_seed,
                    "status": "in_progress",
                    "dataset_average_scores": dataset_averages,
                    "dataset_results": dataset_results,
                },
            ]
            write_json(run_output_dir / "attempt_results.json", attempt_results)
            attempt_results["attempts"].pop()
            logger.info(
                "Attempt %s dataset %s average score: %.4f",
                attempt_number,
                dataset_name,
                average_score,
            )

        overall_average = round(
            sum(dataset_averages.values()) / len(dataset_averages),
            6,
        )
        attempt_record = {
            "attempt_number": attempt_number,
            "attempt_seed": attempt_seed,
            "overall_average_score": overall_average,
            "dataset_average_scores": dataset_averages,
            "dataset_results": dataset_results,
            "within_target_range": args.target_low <= overall_average <= args.target_high,
        }
        attempt_results["attempts"].append(attempt_record)
        logger.info(
            "Attempt %s overall average score: %.4f",
            attempt_number,
            overall_average,
        )

        if attempt_record["within_target_range"]:
            chosen_attempt = attempt_record
            break

    if not chosen_attempt:
        chosen_attempt = choose_attempt(
            attempts=attempt_results["attempts"],
            target_low=args.target_low,
            target_high=args.target_high,
        )

    write_json(run_output_dir / "attempt_results.json", attempt_results)
    write_json(
        run_output_dir / "selected_workflows.json",
        {
            "run_id": run_id,
            "chosen_attempt_number": chosen_attempt["attempt_number"],
            "chosen_attempt_seed": chosen_attempt["attempt_seed"],
            "overall_average_score": chosen_attempt["overall_average_score"],
            "workflows": {
                dataset_name: chosen_attempt["dataset_results"][dataset_name]["workflow"]
                for dataset_name in datasets
            },
        },
    )

    hit_target = args.target_low <= chosen_attempt["overall_average_score"] <= args.target_high
    summary = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "datasets": datasets,
        "samples_per_dataset": args.samples_per_dataset,
        "sample_seed": args.sample_seed,
        "workflow_length": args.workflow_length,
        "model_name": args.model_name,
        "profile_mode": args.profile_mode,
        "tail_tool_datasets": sorted(tail_tool_datasets),
        "tail_tool_name": args.tail_tool_name,
        "forced_pattern": forced_pattern,
        "initial_content": args.initial_content,
        "max_attempts": args.max_attempts,
        "sample_timeout_seconds": args.sample_timeout_seconds,
        "attempts_run": len(attempt_results["attempts"]),
        "target_low": args.target_low,
        "target_high": args.target_high,
        "chosen_attempt_number": chosen_attempt["attempt_number"],
        "chosen_attempt_seed": chosen_attempt["attempt_seed"],
        "chosen_overall_average_score": chosen_attempt["overall_average_score"],
        "chosen_dataset_average_scores": chosen_attempt["dataset_average_scores"],
        "hit_target_range": hit_target,
        "selection_reason": (
            "overall average score landed in target range"
            if hit_target
            else "no attempt hit target range; selected closest score to target center"
        ),
        "artifacts": {
            "sample_manifest": str(run_output_dir / "sample_manifest.json"),
            "attempt_results": str(run_output_dir / "attempt_results.json"),
            "selected_workflows": str(run_output_dir / "selected_workflows.json"),
            "summary": str(run_output_dir / "summary.json"),
        },
    }
    write_json(run_output_dir / "summary.json", summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
