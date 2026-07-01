# AgentXRay

Code release for AgentXRay, accepted to ICML 2026.

AgentXRay searches over collaborative agent workflows for code-generation tasks. This repository includes the core implementation, experiment entry points, ablation configs, and lightweight tests. Datasets are distributed separately from the code repository.

## Repository Structure

```text
AgentXRay/
├── run_experiment.py          # Main experiment entry point
├── requirements.txt           # Python dependencies
├── environment.yml            # Optional Conda environment
├── pyproject.toml             # Package metadata
├── .env.example               # Environment variable template
├── scripts/                   # Utility and baseline scripts
├── src/deagent/               # AgentXRay source package
└── tests/                     # Lightweight framework tests
```

Important source directories:

- `src/deagent/agents/`: agent wrappers and agent profile generation.
- `src/deagent/backends/`: OpenAI-compatible model backend.
- `src/deagent/search/`: MCTS workflow search.
- `src/deagent/tools/`: static analysis and code utility tools.
- `src/deagent/problem_analysis/`: problem parsing and potential scoring.
- `src/deagent/config/`: default, ablation, prompt, model, and reasoning configs.

## Installation

Python 3.9 or newer is required.

Using `venv`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Using Conda:

```bash
conda env create -f environment.yml
conda activate agentxray
pip install -e .
```

## API Configuration

AgentXRay uses an OpenAI-compatible chat completion API. Configure credentials with environment variables. Do not commit real keys into config files.

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://your-openai-compatible-endpoint/v1"
```

`OPENAI_BASE_URL` can be omitted when using the default OpenAI endpoint.

If your endpoint only supports a subset of the models listed in `src/deagent/config/model_library.json`, set the default and allowed models explicitly:

```bash
export DEAGENT_DEFAULT_MODEL="gpt-4o-mini"
export DEAGENT_ALLOWED_MODELS="gpt-4o-mini"
export DEAGENT_LOG_LEVEL="INFO"
```

You can also start from the template:

```bash
cp .env.example .env
set -a
source .env
set +a
```

Then edit `.env` locally. The `.env` file is ignored by git.

## Quick Start

Run a small end-to-end smoke experiment:

```bash
python run_experiment.py \
  --dataset metagpt \
  --data-root /path/to/AgentXRay_Datasets/data \
  --iterations 1 \
  --train-samples 1 \
  --test-samples 1 \
  --run-id metagpt_smoke
```

Run the default MetaGPT experiment:

```bash
python run_experiment.py \
  --dataset metagpt \
  --data-root /path/to/AgentXRay_Datasets/data \
  --iterations 20 \
  --run-id metagpt_demo
```

Outputs are written to:

```text
outputs/<log_dir>/<run-id>/
```

The main result file is:

```text
experiment_results.json
```

Runtime outputs are ignored by git.

## Datasets

Datasets are stored separately from this code repository. You can use the official AgentXRay datasets or bring your own dataset with the same JSON schema.

Official dataset package:

[shiowen/AgentXRay-Datasets](https://huggingface.co/datasets/shiowen/AgentXRay-Datasets)

Download with the Hugging Face CLI:

```bash
hf download shiowen/AgentXRay-Datasets \
  --type dataset \
  --local-dir AgentXRay_Datasets
```

Then either:

1. Place the downloaded `data/` directory inside this repository, or
2. Keep it outside the code checkout and pass `--data-root /path/to/AgentXRay_Datasets/data`.

You can also set the environment variable once:

```bash
export AGENTXRAY_DATA_ROOT="/path/to/AgentXRay_Datasets/data"
```

Built-in dataset names for `--dataset`:

- `atoms`
- `chatdev`
- `eduagent`
- `gemini`
- `gpt`
- `maps`
- `metagpt`

The official dataset layout is:

```text
<data-root>/
├── atoms/
├── chatdev/
├── eduagent/
├── gemini/
├── gpt/
├── maps/
└── metagpt/
```

### Custom Datasets

Custom dataset directories are supported. By default, AgentXRay expects:

```text
<data-root>/<dataset-name>/train.json
<data-root>/<dataset-name>/test.json
```

Run a custom dataset:

```bash
python run_experiment.py \
  --dataset my_dataset \
  --data-root /path/to/my_data_root \
  --iterations 20 \
  --run-id my_dataset_run
```

If your split files use different names, pass them explicitly:

```bash
python run_experiment.py \
  --dataset my_dataset \
  --data-root /path/to/my_data_root \
  --train-file train_alpaca.json \
  --test-file eval_alpaca.json \
  --iterations 20 \
  --run-id my_dataset_run
```

Raw-format files should contain a JSON list of objects:

```json
{
  "folder_name": "example_id",
  "input": "task description",
  "output": "reference output or structured project output"
}
```

Alpaca-format files are also accepted:

```json
{
  "instruction": "task description",
  "input": "",
  "output": "reference output"
}
```

Structured outputs may include fields such as `code_files`, `docs`, `configs`, `logs`, and `requirements`.

Recommended dataset hosting for derivatives:

- Hugging Face Datasets for convenient browsing, versioning, and direct downloads.
- Zenodo for DOI-backed archival snapshots.

## Supported Experiments

The default config is:

```text
src/deagent/config/config.yaml
```

Use a different config with `--config`:

```bash
python run_experiment.py \
  --dataset metagpt \
  --data-root /path/to/AgentXRay_Datasets/data \
  --iterations 20 \
  --config src/deagent/config/exp_baseline.yaml \
  --run-id baseline
```

The codebase supports these experiment modes:

| Experiment | Entry point | Config or flags | Purpose |
| --- | --- | --- | --- |
| Full AgentXRay | `run_experiment.py` | `src/deagent/config/exp_baseline.yaml` | Main workflow-search setting with problem-oriented scoring, tools, and coloring enabled. |
| Agent-only ablation | `run_experiment.py` | `AGENT_ONLY=1` with `src/deagent/config/exp_agent_only.yaml` | Disables tool expansions and evaluates agent-only workflow search. |
| Minimal tool-pool ablation | `run_experiment.py` | `MINIMAL_TOOL_POOL=1` with `src/deagent/config/exp_minimal_tool_pool.yaml` | Restricts tool choices to a compact fixed set. |
| MCTS-only baseline | `run_experiment.py` | `MCTS_BASELINE=1` with `src/deagent/config/exp_mcts_baseline.yaml` | Removes tools, coloring, and enhanced problem-oriented selection. |
| No-coloring ablation | `run_experiment.py` | `src/deagent/config/exp_no_coloring.yaml` | Keeps the main search path but disables red/black coloring and pruning. |
| Pure random tree policy | `run_experiment.py` | `PURE_RANDOM=1` with `src/deagent/config/exp_pure_random.yaml` | Keeps the tree-search pipeline but randomizes policy choices. |
| ATOMS experiments | `run_experiment.py --dataset atoms` | `src/deagent/config/exp_atoms*.yaml` | Runs the same families of experiments on the ATOMS dataset. |
| Direct random workflow baseline | `scripts/run_random_baseline.py` | Script arguments only | Bypasses MCTS and directly samples random workflows for quick baseline comparisons. |

Example ablation commands:

```bash
AGENT_ONLY=1 python run_experiment.py \
  --dataset metagpt \
  --data-root /path/to/AgentXRay_Datasets/data \
  --iterations 20 \
  --config src/deagent/config/exp_agent_only.yaml \
  --run-id agent_only

MINIMAL_TOOL_POOL=1 python run_experiment.py \
  --dataset metagpt \
  --data-root /path/to/AgentXRay_Datasets/data \
  --iterations 20 \
  --config src/deagent/config/exp_minimal_tool_pool.yaml \
  --run-id minimal_tool_pool

MCTS_BASELINE=1 python run_experiment.py \
  --dataset metagpt \
  --data-root /path/to/AgentXRay_Datasets/data \
  --iterations 20 \
  --config src/deagent/config/exp_mcts_baseline.yaml \
  --run-id mcts_baseline

PURE_RANDOM=1 python run_experiment.py \
  --dataset metagpt \
  --data-root /path/to/AgentXRay_Datasets/data \
  --iterations 20 \
  --config src/deagent/config/exp_pure_random.yaml \
  --run-id pure_random
```

ATOMS-specific configs:

- `src/deagent/config/exp_atoms.yaml`
- `src/deagent/config/exp_atoms_agent_only.yaml`
- `src/deagent/config/exp_atoms_mcts_base.yaml`
- `src/deagent/config/exp_atoms_min_tool.yaml`
- `src/deagent/config/exp_atoms_no_coloring.yaml`

### Pure Random vs Direct Random

These two baselines are intentionally different:

| Baseline | Uses MCTS code path? | Builds a search tree? | Randomization point | Intended use |
| --- | --- | --- | --- | --- |
| Pure random tree policy | Yes | Yes | Random node selection and expansion decisions inside the tree-search loop. | Tests whether AgentXRay's search policy is better than random tree traversal under the same pipeline. |
| Direct random workflow baseline | No | No | Randomly samples executable workflow sequences directly. | Tests a simpler non-search baseline that does not benefit from MCTS bookkeeping. |

Run the direct random workflow baseline:

```bash
python scripts/run_random_baseline.py \
  --data-root /path/to/AgentXRay_Datasets/data \
  --datasets chatdev,eduagent,gemini,gpt,metagpt \
  --samples-per-dataset 5
```

## Tests

Run the lightweight framework tests:

```bash
python -m unittest tests/test_basic_framework.py
```

Optional syntax check:

```bash
python -m py_compile $(find src scripts tests -name '*.py' -print) run_experiment.py
```

## License

This project is released under the MIT License. See `LICENSE` for details.

## Reproducibility Notes

- Model access, latency, and output quality depend on the OpenAI-compatible endpoint and available model channels.
- For endpoints with limited model availability, set `DEAGENT_ALLOWED_MODELS` to prevent the search process from selecting unavailable models.
- Use `--train-samples` and `--test-samples` for low-cost smoke tests.
- Full experiments can make many API calls; check model pricing and rate limits before running large configurations.

## Files Excluded From the Release

The GitHub package excludes datasets, generated logs, `outputs/`, virtual environments, Python caches, local databases, IDE metadata, temporary code directories, and large local model/checkpoint files. Source code, scripts, tests, and configs are kept in this repository; datasets should be distributed separately.
