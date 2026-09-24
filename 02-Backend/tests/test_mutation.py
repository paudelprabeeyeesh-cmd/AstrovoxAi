
import pytest
import os
import subprocess


class TestMutationTesting:
    def test_mutmut_installed(self):
        result = subprocess.run(["python", "-m", "mutmut", "--version"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_mutation_config_exists(self):
        config_files = ["mutmut_config.py", ".mutmut", "mutmut.toml"]
        found = any(os.path.isfile(f) for f in config_files)
        assert found

    def test_backend_test_files_exist(self):
        test_files = [
            "tests/test_api.py",
            "tests/test_security.py",
            "tests/test_evaluation.py",
            "tests/test_usage_limits.py",
            "tests/test_cost.py",
        ]
        for f in test_files:
            assert os.path.isfile(f), f"{f} should exist"

    def test_backend_analytics_tests_exist(self):
        assert os.path.isfile("tests/test_usage_tracking.py")
        assert os.path.isfile("tests/test_cost_tracking.py")
        assert os.path.isfile("tests/test_token_tracking.py")
