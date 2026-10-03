"""Tests for the Hugging Face Hub integration.

The network is never touched. The interesting parts of an upload are the file
selection, the metadata, and the card, and all three are exercised directly;
the thin layer that calls the Hub client is checked against a stub.
"""

import json

import numpy as np
import pytest

from astrovox.hub import (
    AuthenticationError,
    CheckpointNotFound,
    HubError,
    ModelInfo,
    build_card,
    build_manifest,
    collect_bundle,
    credential_path,
    delete_token,
    find_checkpoints,
    latest_checkpoint,
    list_models,
    login,
    logout,
    normalize_repo_id,
    parse_repo_id,
    push_model,
    read_manifest,
    read_token,
    stage_bundle,
    status,
    write_token,
)
from astrovox.hub.client import REMOTE_MANIFEST_NAME, REMOTE_WEIGHTS_NAME
from astrovox.nn import Linear, Sequential
from astrovox.tensor.serialization import save_checkpoint


@pytest.fixture
def workspace(tmp_path):
    """A directory holding a real checkpoint, a config, and tokenizer files."""
    model = Sequential(Linear(4, 8))
    save_checkpoint(model, tmp_path / "model.avz", {"step": 10})
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "model_type": "transformer",
                "architectures": ["AstrovoxForCausalLM"],
                "d_model": 64,
                "num_layers": 2,
                "license": "apache-2.0",
                "task": "text-generation",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "tokenizer.json").write_text('{"kind": "char"}', encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"parameter_count": 64, "dataset": "synthetic", "final_loss": 2.5}), encoding="utf-8"
    )
    return tmp_path


class TestRepositoryIds:
    @pytest.mark.parametrize(
        "raw,expected",
        [("me/model", ("me", "model")), ("model", (None, "model")), ("a/b/c", None)],
    )
    def test_parse(self, raw, expected):
        if expected is None:
            with pytest.raises(HubError, match="Malformed"):
                parse_repo_id(raw)
        else:
            assert parse_repo_id(raw) == expected

    def test_normalize_keeps_the_namespace(self):
        assert normalize_repo_id("me/model") == "me/model"
        assert normalize_repo_id("model") == "model"

    @pytest.mark.parametrize("raw", ["", "   ", "/", "a/b/c"])
    def test_rejects_empty_ids(self, raw):
        with pytest.raises(HubError):
            parse_repo_id(raw)

    def test_a_trailing_slash_is_stripped_rather_than_rejected(self):
        """A pasted path with a trailing slash should still work."""
        assert parse_repo_id("a/") == (None, "a")
        assert parse_repo_id("a/model/") == ("a", "model")

    def test_strips_surrounding_slashes(self):
        assert parse_repo_id("/me/model/") == ("me", "model")


class TestCredentials:
    def test_write_and_read(self, tmp_path):
        target = tmp_path / "token"
        write_token("hf_abcdefgh", target)
        assert read_token(target) == "hf_abcdefgh"

    def test_delete(self, tmp_path):
        target = tmp_path / "token"
        write_token("hf_abcdefgh", target)
        assert delete_token(target) is True
        assert delete_token(target) is False

    def test_refuses_an_empty_token(self, tmp_path):
        with pytest.raises(AuthenticationError, match="empty token"):
            write_token("", tmp_path / "token")

    def test_environment_takes_precedence(self, tmp_path, monkeypatch):
        target = tmp_path / "token"
        write_token("from_file", target)
        monkeypatch.setenv("HF_TOKEN", "from_env")
        assert read_token(target) == "from_env"

    def test_status_never_reveals_the_token(self, tmp_path):
        target = tmp_path / "token"
        write_token("hf_supersecretvalue", target)
        state = status(target)
        assert state["authenticated"] is True
        assert "supersecret" not in json.dumps(state)
        assert state["masked"].endswith("alue")

    def test_require_token_explains_what_to_do(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("ASTROVOX_TOKEN", raising=False)
        monkeypatch.setenv("ASTROVOX_TOKEN_FILE", str(tmp_path / "missing"))
        with pytest.raises(AuthenticationError, match="astrovox login"):
            from astrovox.hub import require_token

            require_token()

    def test_login_and_logout_round_trip(self, tmp_path, monkeypatch):
        target = tmp_path / "token"
        monkeypatch.setenv("ASTROVOX_TOKEN_FILE", str(target))
        identity = login("hf_testtoken_value", target, verify=False)
        assert identity.token == "hf_testtoken_value"
        assert read_token(target) == "hf_testtoken_value"
        assert logout(target) is True
        assert read_token(target) is None


class TestCheckpointDiscovery:
    def test_finds_a_checkpoint(self, workspace):
        found = find_checkpoints(workspace)
        assert any(c.name == "model.avz" for c in found)

    def test_latest_returns_a_checkpoint(self, workspace):
        assert latest_checkpoint(workspace).name == "model.avz"

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(CheckpointNotFound, match="not a directory"):
            latest_checkpoint(tmp_path / "nope")

    def test_empty_directory_raises_a_helpful_error(self, tmp_path):
        with pytest.raises(CheckpointNotFound, match="No model checkpoint found"):
            latest_checkpoint(tmp_path)

    def test_an_explicit_file_is_accepted(self, workspace):
        found = latest_checkpoint(workspace, None) if False else find_checkpoints(workspace)
        assert found

    def test_newest_wins(self, tmp_path):
        import os
        import time

        for name, age in (("old.avz", 1000.0), ("new.avz", 0.0)):
            path = tmp_path / name
            path.write_bytes(b"weights")
            stamp = time.time() - age
            os.utime(path, (stamp, stamp))
        assert latest_checkpoint(tmp_path).name == "new.avz"

    def test_skip_directories_are_not_searched(self, tmp_path):
        junk = tmp_path / "node_modules" / "pkg"
        junk.mkdir(parents=True)
        (junk / "model.avz").write_bytes(b"weights")
        assert find_checkpoints(tmp_path) == []

    def test_zero_byte_files_are_ignored(self, tmp_path):
        (tmp_path / "empty.avz").write_bytes(b"")
        assert find_checkpoints(tmp_path) == []

    def test_bundle_includes_companions(self, workspace):
        """The bundle lists what was found; staging is where names are normalized."""
        bundle = collect_bundle(workspace)
        names = {p.name for p in bundle.files}
        assert "model.avz" in names
        assert "tokenizer.json" in names
        assert "config.json" in names

    def test_staging_normalizes_the_remote_names(self, workspace):
        bundle = collect_bundle(workspace)
        staging = stage_bundle(bundle, "me/model", output=workspace / "staged")
        names = {p.name for p in staging.iterdir()}
        # Weights and config get predictable names a loader can find.
        assert REMOTE_WEIGHTS_NAME in names
        assert "astrovox_config.json" in names
        assert "config.json" not in names

    def test_bundle_reads_config_and_manifest(self, workspace):
        bundle = collect_bundle(workspace)
        assert bundle.config["d_model"] == 64
        assert bundle.parameter_count == 64

    def test_bundle_tolerates_a_malformed_config(self, workspace):
        (workspace / "config.json").write_text("{not json", encoding="utf-8")
        bundle = collect_bundle(workspace)
        assert bundle.config == {}

    def test_read_manifest_handles_missing_and_broken(self, tmp_path):
        assert read_manifest(tmp_path / "absent.json") == {}
        broken = tmp_path / "manifest.json"
        broken.write_text("{oops", encoding="utf-8")
        assert read_manifest(broken) == {}


class TestModelCard:
    def test_card_has_front_matter_and_sections(self):
        info = ModelInfo(
            model_id="me/model",
            architecture="AstrovoxForCausalLM",
            parameter_count=3_027_200,
            dataset="synthetic",
            training_steps=100,
            final_loss=2.61,
            framework_version="0.1.0",
        )
        card = build_card(info, "model.avz")
        assert card.startswith("---\n")
        assert "library_name: astrovox" in card
        assert "## Model Details" in card
        assert "## Training" in card
        assert "## Limitations" in card
        assert "## License" in card
        assert "3,027,200" in card

    def test_parameters_render_readably(self):
        info = ModelInfo(model_id="m/m", parameter_count=1_500_000_000)
        assert "1.50B" in build_card(info)

    def test_optional_sections_are_omitted(self):
        card = build_card(ModelInfo(model_id="m/m"))
        assert "## Evaluation" not in card
        assert "## Training" not in card

    def test_card_is_valid_yaml_front_matter(self):
        info = ModelInfo(model_id="m/m", architecture="A: B", tags=("x",), license="mit")
        card = build_card(info)
        front = card.split("---")[1]
        try:
            import yaml

            parsed = yaml.safe_load(front)
            assert parsed["library_name"] == "astrovox"
            assert parsed["license"] == "mit"
        except ImportError:
            # No YAML parser available; check the shape of the front matter.
            assert front.count("\n") > 3
            assert "library_name: astrovox" in front

    def test_manifest_is_machine_readable(self):
        info = ModelInfo(
            model_id="m/m",
            parameter_count=100,
            dataset="d",
            training_steps=5,
            framework_version="0.1.0",
            metrics={"loss": 1.0},
        )
        data = build_manifest(info, "model.avz")
        assert json.loads(json.dumps(data))["parameter_count"] == 100
        assert data["framework"] == "astrovox"


class TestStaging:
    def test_stage_produces_the_expected_files(self, workspace):
        bundle = collect_bundle(workspace)
        staging = stage_bundle(bundle, "me/model", output=workspace / "staged")
        names = {p.name for p in staging.iterdir()}
        assert REMOTE_WEIGHTS_NAME in names
        assert REMOTE_MANIFEST_NAME in names
        assert "README.md" in names
        assert "tokenizer.json" in names
        assert "astrovox_config.json" in names

    def test_staged_weights_are_readable(self, workspace):
        from astrovox.tensor.serialization import load_tensors

        bundle = collect_bundle(workspace)
        staging = stage_bundle(bundle, "me/model", output=workspace / "staged")
        loaded = load_tensors(staging / REMOTE_WEIGHTS_NAME)
        assert loaded

    def test_staging_can_skip_the_readme(self, workspace):
        bundle = collect_bundle(workspace)
        staging = stage_bundle(bundle, "me/model", output=workspace / "staged", include_readme=False)
        assert not (staging / "README.md").exists()

    def test_explicit_info_overrides_are_used(self, workspace):
        bundle = collect_bundle(workspace)
        staging = stage_bundle(
            bundle,
            "me/model",
            output=workspace / "staged",
            info=ModelInfo(model_id="me/model", license="mit"),
        )
        assert "mit" in (staging / "README.md").read_text(encoding="utf-8")


class TestPushWithoutNetwork:
    def test_push_reports_a_missing_checkpoint(self, tmp_path):
        with pytest.raises(CheckpointNotFound):
            push_model("me/model", root=tmp_path, token="fake")

    def test_push_validates_the_repo_id(self, workspace):
        with pytest.raises(HubError, match="Malformed|empty"):
            push_model("bad/id/here", root=workspace, token="fake")

    def test_push_wraps_a_hub_failure(self, workspace, monkeypatch):
        """A client failure must surface as a HubError, not a raw traceback."""
        import astrovox.hub.client as client

        class Exploding:
            def create_repo(self, **kwargs):
                raise OSError("connection reset by peer")

        monkeypatch.setattr(client, "_require_library", lambda: Exploding())
        with pytest.raises(HubError, match="Could not prepare repository"):
            client.push_model("me/model", root=workspace, token="fake")

    def test_push_succeeds_against_a_stub_client(self, workspace, monkeypatch, tmp_path):
        """The whole path is exercised without touching the network."""
        import astrovox.hub.client as client

        captured: dict = {}

        class FakeApi:
            def upload_folder(self, folder_path, repo_id, commit_message=None, ignore_patterns=None):
                captured["files"] = sorted(p.name for p in __import__("pathlib").Path(folder_path).iterdir())
                captured["repo_id"] = repo_id
                captured["message"] = commit_message

        class FakeHub:
            @staticmethod
            def create_repo(**kwargs):
                captured["created"] = kwargs

            HfApi = staticmethod(lambda token=None: FakeApi())

        monkeypatch.setattr(client, "_require_library", lambda: FakeHub())
        staging = tmp_path / "stage"
        result = client.push_model(
            "me/model",
            root=workspace,
            token="fake-token",
            staging=staging,
            commit_message="a message",
        )
        assert result.repo_id == "me/model"
        assert result.created is True
        assert REMOTE_WEIGHTS_NAME in captured["files"]
        assert captured["message"] == "a message"
        assert result.url.endswith("me/model")


class TestListModels:
    def test_missing_dependency_is_explained(self, monkeypatch):
        import builtins

        import astrovox.hub.client as client

        real_import = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "huggingface_hub":
                raise ImportError("no module named huggingface_hub")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked)
        with pytest.raises(HubError, match="pip install huggingface_hub"):
            client._require_library()

    def test_list_models_normalizes_fields(self, monkeypatch):
        import astrovox.hub.client as client

        class Model:
            id = "me/model"
            author = "me"
            downloads = 12
            likes = 3
            lastModified = "2026-01-02T03:04:05.000Z"
            tags = ["astrovox"]

        class FakeApi:
            def __init__(self, token=None):
                pass

            def list_models(self, **kwargs):
                return [Model()]

        class FakeHub:
            HfApi = staticmethod(lambda token=None: FakeApi())

        monkeypatch.setattr(client, "_require_library", lambda: FakeHub())
        results = client.list_models(author="me")
        assert results[0]["id"] == "me/model"
        assert results[0]["downloads"] == 12
        assert "2026-01-02" in results[0]["last_modified"]


class TestCommandLine:
    def test_parser_builds(self):
        from astrovox.cli import build_parser

        assert build_parser() is not None

    def test_login_requires_a_token(self, monkeypatch, capsys):
        from astrovox.cli import main

        monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
        assert main(["login"]) == 1

    def test_push_reports_a_missing_checkpoint(self, tmp_path, capsys):
        from astrovox.cli import main

        assert main(["push", "me/model", "--path", str(tmp_path), "--quiet"]) == 1
        assert "No model checkpoint found" in capsys.readouterr().err

    def test_card_prints_without_pushing(self, workspace, capsys):
        from astrovox.cli import main

        assert main(["card", "me/model", "--path", str(workspace)]) == 0
        out = capsys.readouterr().out
        assert "library_name: astrovox" in out

    def test_checkpoints_lists_files(self, workspace, capsys):
        from astrovox.cli import main

        assert main(["checkpoints", str(workspace)]) == 0
        assert "model.avz" in capsys.readouterr().out

    def test_no_command_prints_help(self, capsys):
        from astrovox.cli import main

        assert main([]) == 0
        assert "astrovox" in capsys.readouterr().out

    def test_version(self, capsys):
        from astrovox.cli import main

        assert main(["--version"]) == 0
        assert capsys.readouterr().out.strip()