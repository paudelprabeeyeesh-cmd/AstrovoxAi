import numpy as np
import pytest

from sandboxing.container_isolation import ContainerConfig


def test_valid_resources_pass():
    cfg = ContainerConfig(image="alpine", cpu_quota="0.5", memory_limit="256m", pids_limit=64)
    cfg.validate_resources()


def test_invalid_cpu_raises():
    cfg = ContainerConfig(image="alpine", cpu_quota="5", memory_limit="256m")
    with pytest.raises(ValueError):
        cfg.validate_resources()


def test_invalid_memory_raises():
    cfg = ContainerConfig(image="alpine", cpu_quota="0.5", memory_limit="16m")
    with pytest.raises(ValueError):
        cfg.validate_resources()


def test_invalid_pids_raises():
    cfg = ContainerConfig(image="alpine", cpu_quota="0.5", memory_limit="256m", pids_limit=0)
    with pytest.raises(ValueError):
        cfg.validate_resources()


def test_build_run_args_includes_limits():
    cfg = ContainerConfig(image="alpine", cpu_quota="1", memory_limit="512m", pids_limit=128)
    args = cfg.build_run_args()
    assert "--cpus=1" in args
    assert "--memory=512m" in args
    assert "--pids-limit=128" in args


def test_build_run_args_read_only():
    cfg = ContainerConfig(image="alpine", read_only_root=True)
    args = cfg.build_run_args()
    assert "--read-only" in args


def test_numpy_resource_boundaries():
    cpus = np.array(["-1", "0", "0.5", "2", "4.1"])
    mems = np.array(["10m", "64m", "256m", "4096m", "5000m"])
    pids = np.array([0, 1, 64, 256, 300])
    for cpu, mem, pid in zip(cpus, mems, pids):
        cfg = ContainerConfig(image="alpine", cpu_quota=cpu, memory_limit=mem, pids_limit=int(pid))
        try:
            cfg.validate_resources()
        except ValueError:
            pass
