import pytest
from sandboxing.microvm_isolation import MicroVMConfig


def test_default_config():
    config = MicroVMConfig()
    assert config.vcpu_count == 1
    assert config.mem_size_mib == 128
    assert config.boot_source == "kernel"
    assert config.kernel_image_path == "/vmlinux"
    assert config.rootfs_image_path == "/rootfs.ext4"
    assert config.fast_boot is True


def test_validate_happy_path():
    config = MicroVMConfig(vcpu_count=2, mem_size_mib=256, boot_source="kernel")
    config.validate()


def test_validate_vcpu_under_min():
    with pytest.raises(ValueError, match="vcpu count out of bounds"):
        MicroVMConfig(vcpu_count=0).validate()


def test_validate_vcpu_over_max():
    with pytest.raises(ValueError, match="vcpu count out of bounds"):
        MicroVMConfig(vcpu_count=5).validate()


def test_validate_memory_under_min():
    with pytest.raises(ValueError, match="memory out of bounds"):
        MicroVMConfig(mem_size_mib=63).validate()


def test_validate_memory_over_max():
    with pytest.raises(ValueError, match="memory out of bounds"):
        MicroVMConfig(mem_size_mib=4097).validate()


def test_validate_empty_boot_source():
    with pytest.raises(ValueError, match="boot source required"):
        MicroVMConfig(boot_source="").validate()


def test_estimated_boot_ms_fast():
    config = MicroVMConfig(fast_boot=True)
    assert config.estimated_boot_ms() == 25


def test_estimated_boot_ms_slow():
    config = MicroVMConfig(fast_boot=False)
    assert config.estimated_boot_ms() == 125


def test_hardware_isolation_summary():
    config = MicroVMConfig(vcpu_count=2, mem_size_mib=256, fast_boot=True)
    summary = config.hardware_isolation_summary()
    assert summary["vcpu_count"] == 2
    assert summary["mem_size_mib"] == 256
    assert summary["isolation_level"] == "hardware"
    assert summary["fast_boot_ms"] == 25


def test_hardware_isolation_summary_invalid():
    config = MicroVMConfig(vcpu_count=0)
    with pytest.raises(ValueError):
        config.hardware_isolation_summary()
