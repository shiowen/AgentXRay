"""Train/test experiment runner."""

import json
import os
import time
from datetime import datetime
import logging
from deagent.utils import logger
from deagent.search import mcts_search
from deagent.evaluation import evaluate_similarity_with_analysis

from deagent.utils.log import output_path as _output_path

os.makedirs(_output_path, exist_ok=True)
_experiment_log_file = os.path.join(_output_path, "training.log")

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)

_fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Add a per-run file handler (avoid duplicates)
_has_this_file = any(
    isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == _experiment_log_file
    for h in _root_logger.handlers
)
if not _has_this_file:
    _fh = logging.FileHandler(_experiment_log_file, encoding='utf-8')
    _fh.setLevel(logging.INFO)
    _fh.setFormatter(_fmt)
    _root_logger.addHandler(_fh)

# Keep a stream handler for interactive runs (avoid duplicates)
_has_stream = any(isinstance(h, logging.StreamHandler) for h in _root_logger.handlers)
if not _has_stream:
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.INFO)
    _sh.setFormatter(_fmt)
    _root_logger.addHandler(_sh)

class ExperimentRunner:
    """Run AgentXRay training and testing against train/test JSON files."""
    
    def __init__(self, data_path: str = "data/metagpt",
                 train_filename: str = "train.json",
                 test_filename: str = "test.json",
                 max_train_samples: int = None,
                 max_test_samples: int = None):
        """Create a runner for a dataset directory."""
        self.data_path = data_path
        self.train_filename = train_filename
        self.test_filename = test_filename
        self.max_train_samples = max_train_samples
        self.max_test_samples = max_test_samples
        self.results = {
            'train': {},
            'test': {},
            'summary': {}
        }
        self.start_time = None

    @staticmethod
    def _load_json_dataset(file_path: str, max_samples: int = None):
        with open(file_path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        if max_samples is not None:
            data = data[:max_samples]
        return data
        
    def run_training_phase(self, iterations: int = 20):
        """Run the MCTS training phase."""

        logger.info("Starting training phase with %s iterations", iterations)
        
        train_file = os.path.join(self.data_path, self.train_filename)
        try:
            train_data = self._load_json_dataset(train_file, self.max_train_samples)
            logger.info("Loaded %d training samples from %s", len(train_data), train_file)
        except FileNotFoundError:
            logger.error("Training file not found: %s", train_file)
            raise

        if not train_data:
            logger.warning("Training dataset is empty; skipping MCTS search")
            self.results['train'] = {
                'status': 'skipped',
                'duration_seconds': 0.0,
                'iterations': iterations,
                'workflow_length': 0,
                'reason': 'Empty training dataset'
            }
            return []
        
        train_start = time.time()
        try:
            logger.info("Running MCTS search")
            best_workflow = mcts_search(train_data, iterations=iterations)
            
            train_duration = time.time() - train_start
            
            self.results['train'] = {
                'status': 'completed',
                'duration_seconds': round(train_duration, 2),
                'iterations': iterations,
                'samples': len(train_data),
                'workflow_length': len(best_workflow) if best_workflow else 0
            }
            
            logger.info(
                "Training completed in %.2f seconds; workflow length=%d",
                train_duration,
                len(best_workflow) if best_workflow else 0,
            )
            return best_workflow
            
        except Exception as e:
            logger.error("Training phase failed: %s", e, exc_info=True)
            self.results['train']['status'] = 'failed'
            self.results['train']['error'] = str(e)
            raise

    def run_test_phase(self, workflow):
        """Run the test phase with a trained workflow."""

        logger.info("Starting test phase")
        
        if not workflow:
            logger.warning("No workflow from training; skipping test phase")
            self.results['test'] = {'status': 'skipped', 'reason': 'No workflow from training.'}
            return 0, []

        test_file = os.path.join(self.data_path, self.test_filename)
        try:
            test_data = self._load_json_dataset(test_file, self.max_test_samples)
            logger.info("Loaded %d test samples from %s", len(test_data), test_file)
        except FileNotFoundError:
            logger.error("Test file not found: %s", test_file)
            raise

        test_start = time.time()
        test_scores = []
        
        for i, sample in enumerate(test_data):
            logger.info("Testing sample %d/%d", i + 1, len(test_data))
            task = sample.get("input", "")
            expected = sample.get("output")
            # Support both structured outputs and plain-code outputs.
            expected_code_files = None
            expected_text = None
            if isinstance(expected, dict):
                expected_code_files = expected.get("code_files")
            elif isinstance(expected, str):
                expected_text = expected

            score, _ = self._execute_workflow_on_sample(
                workflow,
                task,
                expected_output=expected_code_files,
                expected_text=expected_text,
            )
            test_scores.append(score)
            logger.info("Sample %d score: %.3f", i + 1, score)
        
        test_duration = time.time() - test_start
        avg_score = sum(test_scores) / len(test_scores) if test_scores else 0
        
        self.results['test'] = {
            'status': 'completed',
            'duration_seconds': round(test_duration, 2),
            'samples': len(test_data),
            'average_score': round(avg_score, 4),
            'individual_scores': test_scores
        }
        
        logger.info("Testing completed; average score=%.3f", avg_score)
        return avg_score, test_scores

    def _execute_workflow_on_sample(self, workflow, task, expected_output=None, expected_text: str = None):
        """Execute a workflow on one sample and return score plus analysis text."""
        content = ""
        for idx, node in enumerate(workflow):
            provided_content = content
            response = node.action(task, provided_content)
            if response is False or response is None:
                break
            content = response
        
        if content:
            from deagent.utils import codes_to_content, filter_code
            output_code_files = filter_code(content)
            pred_code_content = codes_to_content(output_code_files)

            if expected_text is not None:
                ground_truth_code = expected_text
            else:
                ground_truth_code = codes_to_content(expected_output or {})

            score, analysis_text = evaluate_similarity_with_analysis(pred_code_content, ground_truth_code)
            return score, analysis_text
        else:
            return 0.0, "No output generated by workflow."

    def generate_summary_report(self):
        """Write and return the experiment summary."""

        logger.info("Generating summary report")

        total_duration = time.time() - self.start_time

        results_file = os.path.join(_output_path, "experiment_results.json")
        self.results['summary'] = {
            'experiment_timestamp': datetime.now().isoformat(),
            'total_duration_seconds': round(total_duration, 2),
            'train_status': self.results['train'].get('status', 'not_run'),
            'test_status': self.results['test'].get('status', 'not_run'),
            'final_test_score': self.results['test'].get('average_score', 0.0),
            'output_dir': _output_path,
            'results_file': results_file,
        }

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logger.info("Saved experiment results to %s", results_file)
        return self.results['summary']

    def run_experiment(self, train_iterations: int = 20):
        """Run training, testing, and summary generation."""

        self.start_time = time.time()
        logger.info("Starting train/test experiment")
        logger.info(
            "Experiment config: train_iterations=%s, data_path=%s",
            train_iterations,
            self.data_path,
        )
        
        try:
            workflow = self.run_training_phase(iterations=train_iterations)
            self.run_test_phase(workflow)
            summary = self.generate_summary_report()

            logger.info("Experiment finished successfully")
            logger.info("Final test score: %.3f", summary["final_test_score"])
            logger.info("Total duration: %.2f seconds", summary["total_duration_seconds"])
            
            return True, summary
            
        except Exception as e:
            logger.error("Experiment failed: %s", e, exc_info=True)
            self.generate_summary_report()
            return False, str(e)


def main():
    """Run the default train/test experiment."""

    print("Running AgentXRay simple experiment")
    print("=" * 60)
    
    runner = ExperimentRunner(
        data_path="data/metagpt",
        train_filename="train.json",
        test_filename="test.json",
    )
    
    success, result = runner.run_experiment(train_iterations=20)
    
    if success:
        print("\nExperiment completed")
        print(f"\nSummary:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"\nExperiment failed: {result}")


SimpleTestRunner = ExperimentRunner
