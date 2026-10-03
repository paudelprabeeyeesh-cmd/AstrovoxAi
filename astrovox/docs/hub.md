# Publishing to the Hugging Face Hub

Publish a trained model without assembling an upload by hand. The integration
finds the checkpoint itself, generates a model card, and sends weights,
configuration, tokenizer files, and metadata together.

```bash
astrovox login
astrovox push my-user/astrovox-model
```

## Commands

| Command | What it does |
| --- | --- |
| `astrovox login` | Verify and store an access token |
| `astrovox logout` | Forget the stored token |
| `astrovox whoami` | Show the authenticated account |
| `astrovox push <repo>` | Upload the latest checkpoint |
| `astrovox pull <repo>` | Download a repository |
| `astrovox list-models` | Browse models on the Hub |
| `astrovox card <repo>` | Print the model card without pushing |
| `astrovox checkpoints [dir]` | List the checkpoints found locally |

## Authentication

A token is read from, in order: an explicit `--token` argument, the
`ASTROVOX_TOKEN` or `HF_TOKEN` environment variable, then
`~/.astrovox/token`. The environment wins over the file so a CI job can supply
one without touching the machine.

The token file is written with owner-only permissions, since a token grants
write access to everything the account can reach. It is never logged and never
included in a repository; `astrovox whoami` masks all but the last four
characters.

```bash
astrovox login                                    # prompts
astrovox login hf_xxx --token-file /run/secrets/token
HF_TOKEN=hf_xxx astrovox push me/model            # for CI
```

## Pushing

```bash
astrovox push my-user/astrovox-model
astrovox push my-user/astrovox-model --private
astrovox push my-user/astrovox-model --path runs/exp4 --message "step 4000"
astrovox push me/model --checkpoint runs/exp4/best.avz
```

The checkpoint is discovered rather than named. `astrovox checkpoints` shows
what would be picked:

```
$ astrovox checkpoints runs/exp4
file                                                   size MB  modified
------------------------------------------------------------------------
best.avz                                                50.99  2026-10-03 14:38
last.avz                                                50.99  2026-10-03 14:38
step_2000.avz                                           50.99  2026-10-03 13:02
```

Candidates are ranked by a preference for names like `final`, `best` or
`last`, then by modification time, then by shallowness. Directories that never
hold checkpoints — virtual environments, package caches, build output — are
skipped rather than walked.

The checkpoint is looked for **before** a token is required. It is a local
check, so a user pointing at the wrong directory hears about that rather than
about authentication.

## What gets uploaded

The set is assembled into a staging directory first, then uploaded. That makes
the file list inspectable without a network, and the same set is used for both.

```
model.avz              weights, renamed from whatever they were called locally
astrovox_config.json   configuration, renamed from config.json
astrovox_manifest.json machine-readable metadata
tokenizer.json         any tokenizer file found beside the checkpoint
README.md              the generated model card
```

Weights and configuration get predictable names because a downstream loader
should not have to know what the training script happened to call them.

Use `--staging DIR` to keep the assembled files for inspection.

## The model card

Generated from the checkpoint's manifest, its configuration, and any
metadata files beside it. The front matter is YAML, which is what the Hub
reads to populate a model page.

```markdown
---
language: en
license: apache-2.0
library_name: astrovox
tags:
  - astrovox
  - transformer
task: text-generation
---

# my-user/astrovox-model

| File | Purpose |
|---|---|
| `model.avz` | Model weights |

## Model Details

| Property | Value |
|---|---|
| Architecture | AstrovoxForCausalLM |
| Parameters | 3,027,200 (3.03M) |
| Astrovox version | 0.1.0 |
| Training steps | 4,000 |
| Final loss | 2.6100 |
```

Sections appear only when there is something to put in them: a model with no
recorded metrics gets no Evaluation section rather than an empty one. Preview
it before uploading with `astrovox card my-user/astrovox-model`.

## Pulling

```bash
astrovox pull my-user/astrovox-model
astrovox pull my-user/astrovox-model --path models/llama --revision v2
```

Prints the directory it downloaded into. A repository that does not exist is
reported as such rather than as a generic download failure.

## Using a downloaded model

```python
from astrovox import tensor
from astrovox.hub import pull_model

directory = pull_model("my-user/astrovox-model", directory="models/mine").directory
from astrovox.tensor.serialization import load_checkpoint

model = Sequential(...)          # built to match the configuration
load_checkpoint(model, directory / "model.avz")
```

## Programmatic use

```python
from astrovox.hub import ModelInfo, collect_bundle, push_model, stage_bundle

bundle = collect_bundle("runs/exp4")
info = ModelInfo.from_bundle("me/model", bundle, license="mit")

result = push_model(
    "me/model",
    root="runs/exp4",
    info=info,
    progress=print,          # upload progress
)
print(result.url)
```

`push_model` returns a `PushResult` with the repository, whether it was
created, and the files uploaded.

## Error handling

Failures are typed rather than raw:

| Exception | Raised when |
| --- | --- |
| `AuthenticationError` | No usable token, or it does not verify |
| `CheckpointNotFound` | No trained artifact under the search root |
| `RepositoryNotFound` | The repository being pulled does not exist |
| `HubError` | The upload or download failed |
| `HubError` | `huggingface_hub` is not installed |

Every message says what to do next. The CLI writes progress to standard error
and results to standard output, so `astrovox pull ... | read` works, and exits
non-zero on failure so the commands compose in a script.

## Dependency

The integration uses the official `huggingface_hub` package rather than
hand-rolled HTTP, so authentication, retries, and resumable transfers come
from the client that maintains them. It is imported lazily: everything else in
Astrovox works without it, and only these operations need it.

```bash
pip install huggingface_hub
```

## Tests

`astrovox/tests/test_hub.py` runs without a network. Repository id parsing,
credential handling, checkpoint discovery, card rendering, staging, and the
push path are all exercised directly; the layer that calls the Hub client is
checked against a stub, so a failure in that thin layer is still caught
without needing a token.