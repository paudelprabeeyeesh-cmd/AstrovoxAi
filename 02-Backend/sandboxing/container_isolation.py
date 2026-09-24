import json
from dataclasses import dataclass


@dataclass
class ContainerConfig:
    image: str
    cpu_quota: str = "0.5"
    memory_limit: str = "256m"
    pids_limit: int = 64
    seccomp_profile: str = "default"
    read_only_root: bool = True

    def validate_resources(self) -> None:
        cpu = float(self.cpu_quota)
        mem = int(self.memory_limit.lower().replace("m", ""))
        pids = int(self.pids_limit)
        if cpu <= 0 or cpu > 4:
            raise ValueError("cpu quota out of bounds")
        if mem < 64 or mem > 4096:
            raise ValueError("memory limit out of bounds")
        if pids < 1 or pids > 256:
            raise ValueError("pids limit out of bounds")

    def build_run_args(self) -> List[str]:
        self.validate_resources()
        args = [
            "docker", "run", "--rm",
            f"--cpus={self.cpu_quota}",
            f"--memory={self.memory_limit}",
            f"--pids-limit={self.pids_limit}",
        ]
        if self.read_only_root:
            args.append("--read-only")
        if self.seccomp_profile and self.seccomp_profile != "default":
            args.extend(["--security-opt", f"seccomp={self.seccomp_profile}"])
        args.append(self.image)
        return args

    def seccomp_policy(self) -> dict:
        if self.seccomp_profile == "default":
            return {"defaultAction": "SCMP_ACT_ERRNO", "syscalls": []}
        try:
            return json.loads(self.seccomp_profile)
        except json.JSONDecodeError:
            raise ValueError("invalid seccomp profile")
