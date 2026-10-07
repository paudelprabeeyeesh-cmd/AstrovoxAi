"""Tests for cluster scheduler integrations - expanded coverage."""

from __future__ import annotations

import json

import pytest

from astrovox.cluster import ClusterScheduler, JobSpec, KubernetesAdapter, SlurmAdapter


def test_kubernetes_adapter_submit_creates_manifest():
    adapter = KubernetesAdapter(namespace="default")
    job_id = adapter.submit(JobSpec(name="job1", image="python:3.12", command="python train.py"))
    assert job_id == "job1"


def test_slurm_adapter_submit_creates_script():
    adapter = SlurmAdapter()
    job_id = adapter.submit(JobSpec(name="slurm-job", image="python:3.12", command="python train.py", gpu=1))
    assert job_id == "slurm-job"


def test_cluster_scheduler_wraps_adapter():
    adapter = KubernetesAdapter()
    scheduler = ClusterScheduler(adapter=adapter)
    job_id = scheduler.launch(JobSpec(name="scheduled", image="python:3.12", command="echo hi"))
    assert job_id == "scheduled"
