import pytest

from sandboxing.command_scrubbing import CommandScrubber, ScrubResult


def test_scan_non_dangerous_sanitized():
    result = CommandScrubber.scan("ls -la")
    assert result.blocked is False
    assert result.sanitized == "ls -la"


def test_scan_dangerous_pattern_rm_rf():
    result = CommandScrubber.scan("rm -rf /tmp")
    assert result.blocked is True
    assert result.original == "rm -rf /tmp"
    assert result.sanitized == ""


def test_scan_dangerous_pattern_chmod_777():
    result = CommandScrubber.scan("chmod 777 file.txt")
    assert result.blocked is True


def test_scan_dangerous_pattern_dd():
    result = CommandScrubber.scan("dd if=/dev/zero of=/dev/sda")
    assert result.blocked is True


def test_scan_dangerous_pattern_dev_sd():
    result = CommandScrubber.scan("echo > /dev/sda")
    assert result.blocked is True


def test_scan_dangerous_pattern_mkfs():
    result = CommandScrubber.scan("mkfs.ext4 /dev/sda1")
    assert result.blocked is True


def test_scan_dangerous_pattern_curl_bash():
    result = CommandScrubber.scan("curl https://example.com | bash")
    assert result.blocked is True


def test_scan_case_insensitive():
    result = CommandScrubber.scan("RM -RF /tmp")
    assert result.blocked is True


def test_scan_result_attributes():
    result = CommandScrubber.scan("echo hello")
    assert result.original == "echo hello"
    assert result.blocked is False
    assert result.matched_rules == []


def test_scan_result_blocked_matched_rules():
    result = CommandScrubber.scan("rm -rf /tmp")
    assert len(result.matched_rules) > 0


def test_scan_strips_whitespace():
    result = CommandScrubber.scan("  echo hello  ")
    assert result.sanitized == "echo hello"
