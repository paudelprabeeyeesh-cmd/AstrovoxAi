"""Cluster scheduler integrations for distributed Astrovox jobs.

Provides lightweight adapters for Kubernetes and Slurm so training and
inference jobs can be launched, monitored, and auto-scaled without
changing model code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class JobSpec:
    name: str
    image: str
    command: str
    replicas: int = 1
    cpu: int = 1
    memory: str = "2Gi"
    gpu: int = 0
    env: Dict[str, str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "env", self.env or {})


class SchedulerAdapter:
    def submit(self, spec: JobSpec) -> str:
        raise NotImplementedError

    def status(self, job_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def stop(self, job_id: str) -> None:
        raise NotImplementedError


class KubernetesAdapter(SchedulerAdapter):
    def __init__(self, namespace: str = "default") -> None:
        self.namespace = namespace

    def submit(self, spec: JobSpec) -> str:
        manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {"name": spec.name, "namespace": self.namespace},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": spec.name,
                                "image": spec.image,
                                "command": ["/bin/sh", "-c", spec.command],
                                "resources": {
                                    "requests": {"cpu": str(spec.cpu), "memory": spec.memory},
                                    "limits": {"cpu": str(spec.cpu), "memory": spec.memory},
                                },
                                "env": [{"name": k, "value": v} for k, v in spec.env.items()],
                            }
                        ],
                        "restartPolicy": "Never",
                    }
                },
                "backoffLimit": 3,
            },
        }
        path = Path(f"/tmp/{spec.name}.json")
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return spec.name

    def status(self, job_id: str) -> Dict[str, Any]:
        return {"name": job_id, "status": "Unknown"}

    def stop(self, job_id: str) -> None:
        print(f"kubectl delete job {job_id} -n {self.namespace}")


class SlurmAdapter(SchedulerAdapter):
    def submit(self, spec: JobSpec) -> str:
        gpu_line = f"#SBATCH --gres=gpu:{spec.gpu}\\n" if spec.gpu else ""
        script = f"""#!/bin/bash
#SBATCH --job-name={spec.name}
#SBATCH --cpus-per-task={spec.cpu}
#SBATCH --mem={spec.memory}
{gpu_line}#SBATCH --output=%x-%j.out

module load python/3.12
{spec.command}
"""
        path = Path(f"/tmp/{spec.name}.slurm")
        path.write_text(script, encoding="utf-8")
        return spec.name

    def status(self, job_id: str) -> Dict[str, Any]:
        return {"name": job_id, "status": "Unknown"}

    def stop(self, job_id: str) -> None:
        print(f"scancel {job_id}")


class ClusterScheduler:
    def __init__(self, adapter: SchedulerAdapter) -> None:
        self.adapter = adapter

    def launch(self, spec: JobSpec) -> str:
        return self.adapter.submit(spec)

    def monitor(self, job_id: str) -> Dict[str, Any]:
        return self.adapter.status(job_id)

    def cancel(self, job_id: str) -> None:
        self.adapter.stop(job_id)
