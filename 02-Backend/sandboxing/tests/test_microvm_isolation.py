import numpy as np
import pytest

from sandboxing.microvm_isolation import MicroVMConfig


def test_valid_config():
    cfg = MicroVMConfig(vcpu_count=1, mem_size_mib=128)
    summary = cfg.hardware_isolation_summary()
    assert summary["isolation_level"] == "hardware"


def test_fast_boot_estimate():
    cfg = MicroVMConfig(fast_boot=True)
    assert cfg.estimated_boot_ms() == 25


def test_slow_boot_estimate():
    cfg = MicroVMConfig(fast_boot=False)
    assert cfg.estimated_boot_ms() == 125


def test_invalid_vcpu_raises():
    cfg = MicroVMConfig(vcpu_count=0)
    with pytest.raises(ValueError):
        cfg.validate()


def test_invalid_memory_raises():
    cfg = MicroVMConfig(mem_size_mib=32)
    with pytest.raises(ValueError):
        cfg.validate()


def test_numpy_summary_matrix():
    vcpus = np.array([1, 2, 4])
    mems = np.array([128, 512, 2048])
    for vcpu, mem in zip(vcpus, mems):
        cfg = MicroVMConfig(vcpu_count=int(vcpu), mem_size_mib=int(mem))
        summary = cfg.hardware_isolation_summary()
        assert summary["vcpu_count"] == int(vcpu)
        assert summary["mem_size_mib"] == int(mem)
