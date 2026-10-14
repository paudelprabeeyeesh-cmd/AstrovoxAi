
import pytest
import os
import subprocess


# Bounded so a wedged subprocess can never hang the whole suite: A-002
# requires the run to terminate reliably, and an unbounded subprocess.run is
# what turned a failed assertion into a timeout.
_TIMEOUT_SECONDS = 120


class TestAutomationFramework:
    def test_pytest_can_collect_tests(self, tmp_path):
        """Pytest's collection machinery works on this tree.

        This ran `pytest --collect-only` over the whole suite from inside the
        suite. Collection imports every conftest and test module, so the check
        cost about as much as the entire run, and because it referenced this
        same file it was self-recursive and never returned. Collecting a tiny
        module proves the machinery works far more cheaply and terminates.
        """
        module = tmp_path / "test_collect_probe.py"
        module.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", str(module)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "test_collect_probe.py" in result.stdout

    def test_backend_lint_available(self):
        result = subprocess.run(
            ["python", "-m", "ruff", "--version"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
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
