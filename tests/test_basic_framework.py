"""Core framework smoke tests."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
sys.path.insert(0, SRC_ROOT)

from deagent.config import config
from deagent.reporting import SafeJSONEncoder, safe_json_dump, sanitize_report_data
from deagent.tools.path_utils import safe_join
import deagent.utils.codes as codes_module
from deagent.utils.codes import codes_to_content, filter_code
from deagent.utils.log import setup_logger


class TestJSONSerialization(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_datetime_serialization(self):
        test_data = {
            "timestamp": datetime.now(),
            "start_time": datetime(2025, 1, 1, 12, 0, 0),
        }

        json_str = json.dumps(test_data, cls=SafeJSONEncoder)
        loaded_data = json.loads(json_str)

        self.assertIn("timestamp", loaded_data)
        self.assertIn("start_time", loaded_data)

    def test_decimal_serialization(self):
        test_data = {"score": Decimal("0.85"), "accuracy": Decimal("87.5")}

        loaded_data = json.loads(json.dumps(test_data, cls=SafeJSONEncoder))

        self.assertIsInstance(loaded_data["score"], float)
        self.assertIsInstance(loaded_data["accuracy"], float)

    def test_set_serialization(self):
        test_data = {
            "tools": {"compiler", "empty_detect", "validator"},
            "models": {"gpt-4", "claude-3"},
        }

        loaded_data = json.loads(json.dumps(test_data, cls=SafeJSONEncoder))

        self.assertIsInstance(loaded_data["tools"], list)
        self.assertIsInstance(loaded_data["models"], list)

    def test_exception_serialization(self):
        test_data = {"error": ValueError("Test error message")}

        loaded_data = json.loads(json.dumps(test_data, cls=SafeJSONEncoder))

        self.assertIn("error", loaded_data)
        self.assertEqual(loaded_data["error"]["exception_type"], "ValueError")

    def test_safe_json_dump(self):
        test_data = {
            "timestamp": datetime.now(),
            "score": Decimal("0.95"),
            "tools": {"tool1", "tool2"},
            "nested": {"error": Exception("test error"), "data": [1, 2, 3]},
        }
        test_file = os.path.join(self.test_dir, "test_output.json")

        self.assertTrue(safe_json_dump(test_data, test_file))
        self.assertTrue(os.path.exists(test_file))

        with open(test_file, "r", encoding="utf-8") as handle:
            loaded_data = json.load(handle)

        self.assertIn("timestamp", loaded_data)
        self.assertIn("score", loaded_data)

    def test_sanitize_report_data(self):
        test_data = {
            "timestamp": datetime.now(),
            "score": 0.85,
            "nested": {"sub_timestamp": datetime.now(), "values": [1, 2, 3]},
            "execution_time": 123.456789,
        }

        sanitized = sanitize_report_data(test_data)

        self.assertIsInstance(sanitized["timestamp"], str)
        self.assertIsInstance(sanitized["nested"]["sub_timestamp"], str)
        self.assertEqual(sanitized["execution_time"], 123.457)


class TestFileOperations(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_filter_code_functionality(self):
        test_content = """
        main.py
        ```python
        def main():
            print("Hello World")
            return 0
        ```

        utils.py
        ```python
        def helper():
            return "helper"
        ```
        """

        codebooks = filter_code(test_content)

        self.assertIn("main.py", codebooks)
        self.assertIn("utils.py", codebooks)
        self.assertIn("print", codebooks["main.py"])

    def test_codes_to_content(self):
        codebooks = {
            "main.py": "def main():\n    return 0",
            "utils.py": "def helper():\n    return 'help'",
        }

        content = codes_to_content(codebooks)

        self.assertIn("main.py", content)
        self.assertIn("utils.py", content)
        self.assertIn("def main", content)

    def test_filter_code_preserves_nested_paths(self):
        test_content = """
        File: package/utils.py
        ```python
        def helper():
            return "helper"
        ```
        """

        codebooks = filter_code(test_content)

        self.assertIn("package/utils.py", codebooks)

    def test_save_codes_file_handles_nested_and_unsafe_paths(self):
        original_output_path = codes_module.output_path
        codes_module.output_path = self.test_dir
        try:
            codes_module.save_codes_file(
                {
                    "package/utils.py": "def helper():\n    return 'helper'",
                    "../escape.py": "raise RuntimeError('should not be written')",
                }
            )
            generated_dirs = [
                name for name in os.listdir(self.test_dir)
                if os.path.isdir(os.path.join(self.test_dir, name))
            ]
            self.assertEqual(len(generated_dirs), 1)
            generated_root = os.path.join(self.test_dir, generated_dirs[0])

            self.assertTrue(os.path.exists(os.path.join(generated_root, "package", "utils.py")))
            self.assertFalse(os.path.exists(os.path.join(self.test_dir, "escape.py")))
        finally:
            codes_module.output_path = original_output_path

    def test_safe_join_rejects_directory_escape(self):
        safe_path = safe_join(self.test_dir, "package/module.py")

        self.assertTrue(os.path.realpath(safe_path).startswith(os.path.realpath(self.test_dir)))
        with self.assertRaises(ValueError):
            safe_join(self.test_dir, "../escape.py")

    def test_directory_creation(self):
        nested_path = os.path.join(self.test_dir, "level1", "level2", "level3")

        os.makedirs(nested_path, exist_ok=True)
        os.makedirs(nested_path, exist_ok=True)

        self.assertTrue(os.path.exists(nested_path))


class TestConfigLoading(unittest.TestCase):
    def test_yaml_config_structure(self):
        for key in ["model", "mcts_tree", "log"]:
            self.assertIn(key, config, f"Missing required config key: {key}")

        self.assertIn("openai_api_key", config.get("model", {}))
        self.assertIn("max_retry_number", config.get("model", {}))
        self.assertIn("max_child_number", config.get("mcts_tree", {}))
        self.assertIn("max_depth", config.get("mcts_tree", {}))

    def test_config_values_validity(self):
        mcts_config = config.get("mcts_tree", {})

        max_children = mcts_config.get("max_child_number", 0)
        max_depth = mcts_config.get("max_depth", 0)

        self.assertGreater(max_children, 0)
        self.assertGreater(max_depth, 0)
        self.assertLess(max_children, 100)
        self.assertLess(max_depth, 50)


class TestLoggingSystem(unittest.TestCase):
    def test_logger_creation(self):
        test_log_file = os.path.join(tempfile.gettempdir(), "deagent_test_log.txt")

        try:
            test_logger = setup_logger("test_logger", test_log_file)
            test_logger.info("Test info message")
            test_logger.warning("Test warning message")
            test_logger.error("Test error message")

            self.assertTrue(os.path.exists(test_log_file))

            with open(test_log_file, "r", encoding="utf-8") as handle:
                log_content = handle.read()

            self.assertIn("Test info message", log_content)
            self.assertIn("Test warning message", log_content)
            self.assertIn("Test error message", log_content)
        finally:
            if os.path.exists(test_log_file):
                os.remove(test_log_file)


class TestErrorHandling(unittest.TestCase):
    def test_graceful_error_handling(self):
        self.assertFalse(safe_json_dump({"test": "data"}, "/non/existent/path/file.json"))

    def test_data_corruption_handling(self):
        problematic_data = {
            "function": lambda x: x + 1,
            "normal_data": "this is fine",
            "datetime": datetime.now(),
        }

        loaded = json.loads(json.dumps(problematic_data, cls=SafeJSONEncoder))

        self.assertIn("normal_data", loaded)
        self.assertEqual(loaded["normal_data"], "this is fine")


if __name__ == "__main__":
    unittest.main()
