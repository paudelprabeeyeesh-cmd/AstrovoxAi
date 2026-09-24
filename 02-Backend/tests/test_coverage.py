
import pytest
import os
import subprocess


class TestCoverageReporting:
    def test_pytest_coverage_command_exists(self):
        result = subprocess.run(["python", "-m", "pytest", "--version"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_python_coverage_module_exists(self):
        result = subprocess.run(["python", "-c", "import coverage"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_backend_tests_directory_exists(self):
        assert os.path.isdir("tests")

    def test_backend_has_pytest_ini(self):
        assert os.path.isfile("pytest.ini")

    def test_frontend_has_jest_config(self):
        assert os.path.isfile("../apps/web/jest.config.js")

    def test_frontend_has_package_json(self):
        assert os.path.isfile("../apps/web/package.json")

    def test_backend_has_analytics_module(self):
        assert os.path.isfile("app/analytics/__init__.py")
        assert os.path.isfile("app/analytics/core.py")

    def test_backend_has_evaluation_module(self):
        assert os.path.isfile("app/evaluation/evaluation_suite.py")

    def test_backend_has_chaos_testing(self):
        assert os.path.isfile("app/chaos_testing.py")

    def test_backend_has_load_test(self):
        assert os.path.isfile("app/load_test.py")

    def test_backend_has_pen_test(self):
        assert os.path.isfile("app/pen_test.py")
