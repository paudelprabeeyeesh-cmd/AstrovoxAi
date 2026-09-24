from dataclasses import dataclass


@dataclass
class MicroVMConfig:
    vcpu_count: int = 1
    mem_size_mib: int = 128
    boot_source: str = "kernel"
    kernel_image_path: str = "/vmlinux"
    rootfs_image_path: str = "/rootfs.ext4"
    fast_boot: bool = True

    def validate(self) -> None:
        if not 1 <= self.vcpu_count <= 4:
            raise ValueError("vcpu count out of bounds")
        if not 64 <= self.mem_size_mib <= 4096:
            raise ValueError("memory out of bounds")
        if not self.boot_source:
            raise ValueError("boot source required")

    def estimated_boot_ms(self) -> int:
        if self.fast_boot:
            return 25
        return 125

    def hardware_isolation_summary(self) -> dict:
        self.validate()
        return {
            "vcpu_count": self.vcpu_count,
            "mem_size_mib": self.mem_size_mib,
            "boot_source": self.boot_source,
            "fast_boot_ms": self.estimated_boot_ms(),
            "isolation_level": "hardware",
        }
