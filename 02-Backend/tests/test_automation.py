
import pytest
import os
import subprocess


class TestAutomationFramework:
    def test_pytest_can_collect_tests(self):
        result = subprocess.run(["python", "-m", "pytest", "--collect-only", "-q"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_backend_lint_available(self):
        result = subprocess.run(["python", "-m", "ruff", "--version"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_frontend_test_script_exists(self):
        assert os.path.isfile("../apps/web/package.json")
        with open("../apps/web/package.json") as f:
            import json
            pkg = json.load(f)
            assert "test" in pkg.get("scripts", {})

    def test_frontend_e2e_directory_can_exist(self):
        e2e_dir = "../apps/web/__tests__/e2e"
        assert os.path.isdir(e2e_dir) or not os.path.exists(e2e_dir)

    def test_backend_has_makefile_or_equivalent(self):
        build_files = ["Makefile", "scripts", "tasks.py"]
        found = any(os.path.exists(f) for f in build_files)
        assert found
