"""Hugging Face Hub integration.

Publish a trained Astrovox model without assembling the upload by hand::

    astrovox login
    astrovox push my-user/astrovox-model
    astrovox pull my-user/astrovox-model

The integration finds the checkpoint itself, generates a model card, and
uploads weights, configuration, tokenizer files, and metadata together.
"""

from astrovox.hub.auth import (
    AuthenticationError,
    Identity,
    credential_path,
    delete_token,
    login,
    logout,
    read_token,
    require_token,
    status,
    whoami,
    write_token,
)
from astrovox.hub.card import (
    ModelInfo,
    build_card,
    build_manifest,
    write_card,
)
from astrovox.hub.checkpoint import (
    Checkpoint,
    CheckpointNotFound,
    ModelBundle,
    architecture_of,
    collect_bundle,
    find_checkpoints,
    latest_checkpoint,
    parameter_count_of,
    read_manifest,
)
from astrovox.hub.client import (
    REMOTE_MANIFEST_NAME,
    REMOTE_WEIGHTS_NAME,
    HubError,
    PullResult,
    PushResult,
    RepositoryNotFound,
    describe_local_model,
    list_models,
    model_card,
    normalize_repo_id,
    parse_repo_id,
    pull_model,
    push_model,
    repo_info,
    stage_bundle,
)

__all__ = [
    "AuthenticationError",
    "Checkpoint",
    "CheckpointNotFound",
    "HubError",
    "Identity",
    "ModelBundle",
    "ModelInfo",
    "PullResult",
    "PushResult",
    "REMOTE_MANIFEST_NAME",
    "REMOTE_WEIGHTS_NAME",
    "RepositoryNotFound",
    "architecture_of",
    "build_card",
    "build_manifest",
    "collect_bundle",
    "credential_path",
    "delete_token",
    "describe_local_model",
    "find_checkpoints",
    "latest_checkpoint",
    "list_models",
    "login",
    "logout",
    "model_card",
    "normalize_repo_id",
    "parameter_count_of",
    "parse_repo_id",
    "pull_model",
    "push_model",
    "read_manifest",
    "read_token",
    "repo_info",
    "require_token",
    "stage_bundle",
    "status",
    "whoami",
    "write_card",
    "write_token",
]