import pytest

from sandboxing.container_isolation import ContainerConfig


def test_default_config():
    config = ContainerConfig(image="python:3.11")
    assert config.image == "python:3.11"
    assert config.cpu_quota == "0.5"
    assert config.memory_limit == "256m"
    assert config.pids_limit == 64
    assert config.seccomp_profile == "default"
    assert config.read_only_root is True


def test_validate_resources_happy_path():
    config = ContainerConfig(image="python:3.11")
    config.validate_resources()


def test_validate_resources_cpu_under_min():
    with pytest.raises(ValueError, match="cpu quota out of bounds"):
        ContainerConfig(image="python:3.11", cpu_quota="0").validate_resources()


def test_validate_resources_cpu_over_max():
    with pytest.raises(ValueError, match="cpu quota out of bounds"):
        ContainerConfig(image="python:3.11", cpu_quota="5").validate_resources()


def test_validate_resources_memory_under_min():
    with pytest.raises(ValueError, match="memory limit out of bounds"):
        ContainerConfig(image="python:3.11", memory_limit="63m").validate_resources()


def test_validate_resources_memory_over_max():
    with pytest.raises(ValueError, match="memory limit out of bounds"):
        ContainerConfig(image="python:3.11", memory_limit="4097m").validate_resources()


def test_validate_resources_pids_under_min():
    with pytest.raises(ValueError, match="pids limit out of bounds"):
        ContainerConfig(image="python:3.11", pids_limit=0).validate_resources()


def test_validate_resources_pids_over_max():
    with pytest.raises(ValueError, match="pids limit out of bounds"):
        ContainerConfig(image="python:3.11", pids_limit=257).validate_resources()


def test_build_run_args_defaults():
    config = ContainerConfig(image="python:3.11")
    args = config.build_run_args()
    assert args[0] == "docker"
    assert args[1] == "run"
    assert args[2] == "--rm"
    assert "--read-only" in args
    assert "python:3.11" in args


def test_build_run_args_custom_resources():
    config = ContainerConfig(image="python:3.11", cpu_quota="2.0", memory_limit="512m", pids_limit=128)
    args = config.build_run_args()
    assert "--cpus=2.0" in args
    assert "--memory=512m" in args
    assert "--pids-limit=128" in args


def test_build_run_args_no_read_only():
    config = ContainerConfig(image="python:3.11", read_only_root=False)
    args = config.build_run_args()
    assert "--read-only" not in args


def test_build_run_args_custom_seccomp():
    config = ContainerConfig(image="python:3.11", seccomp_profile='{"defaultAction":"SCMP_ACT_ERRNO"}')
    args = config.build_run_args()
    assert "--security-opt" in args
    assert "seccomp=" in " ".join(args)


def test_seccomp_policy_default():
    config = ContainerConfig(image="python:3.11")
    policy = config.seccomp_policy()
    assert policy["defaultAction"] == "SCMP_ACT_ERRNO"


def test_seccomp_policy_custom():
    config = ContainerConfig(image="python:3.11", seccomp_profile='{"syscalls":[]}')
    policy = config.seccomp_policy()
    assert policy["syscalls"] == []


def test_seccomp_policy_invalid_json():
    config = ContainerConfig(image="python:3.11", seccomp_profile="not-json")
    with pytest.raises(ValueError, match="invalid seccomp profile"):
        config.seccomp_policy()
