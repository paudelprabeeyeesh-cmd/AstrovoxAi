# Neural Lab: repository audit and first milestone

## Verified architecture

- The product backend is the Python FastAPI application in `02-Backend/`; it routes chat requests through provider adapters. The repository's own `docs/MODULE_INVENTORY.md` describes only a small subset of the many experimental top-level Python modules as imported by the product.
- The standalone Go engine (`tensor/`, `autograd/`, `model/`, `cmd/`) is a separate project. The root `AGENTS.md` explicitly says it does not serve the FastAPI app, and the FastAPI app does not call it.
- There is also an experimental PyTorch Transformer under `models/llm/model/`, plus pretraining scripts and configs. The checked-in default config is named `config_40b.yaml` and specifies a 5,120-wide, 40-layer network; that is not an appropriate 4 GB training profile. Its pretraining path constructs a model from a config and runs AdamW; it is not evidence that a model has been successfully trained or connected to the product chat path.
- The existing product chat implementation is provider-routed; no product default model was replaced or redirected by this milestone. No existing checkpoint was loaded, removed, or modified.
- Existing tokenizer training code accepts whole lists of texts and defaults to a vocabulary of 50,257; it is not the bounded-memory character-tokenizer path introduced here.

## Milestone delivered

An isolated `neural_lab` package now has a PyTorch MLP and causal Transformer using real autograd, configurable initialization seed, AdamW/Adam/SGD optimizers, a streaming UTF-8 character vocabulary scan with a 16 MiB input cap and a 4,096-character vocabulary ceiling, a conservative RAM admission estimate, and a streaming training loop. Jobs record actual epoch/step/loss/RSS, write atomic checkpoints, resume model and optimizer state while reconstructing the streaming data cursor from the saved step, and support cooperative cancellation. A process-wide OS lock prevents simultaneous training jobs. Validation loss is `null` when no complete held-out sequence exists. Dataset handling validates and deduplicates `.txt`/`.md` files, records provenance/license notes and measured text statistics, bounds previews, and requires explicit deletion confirmation. A local model registry supports completed runs, explicit experimental selection, rollback, checkpoint evaluation, and text generation without changing production chat inference.

The neural subsystem remains experimental and separate from chat inference. Its product-facing FastAPI routes and dashboard use Supabase RLS metadata and user-scoped local artifact storage; the standalone CLI and package remain available for local experiments.

## Windows quick start

Use the repository's existing Python environment with PyTorch installed. No CUDA or model download is required.

```powershell
cd C:\Users\Dell\Documents\GitHub\AstrovoxAi
python -m neural_lab.cli train --dataset path\to\small-utf8.txt --output neural_lab_runs\first --steps 10 --seed 17 --optimizer adamw
python -m neural_lab.cli train --dataset path\to\small-utf8.txt --output neural_lab_runs\second --steps 20 --seed 17 --resume neural_lab_runs\first\checkpoints\step-10.pt
python -m pytest tests\test_neural_lab.py tests\test_neural_lab_api.py tests\test_neural_lab_upload_api.py tests\test_neural_lab_tenant.py tests\test_neural_lab_job_api.py -q
```

PyTorch and psutil are already declared in the repository's requirements and were available in the tested environment; this change did not install packages or download models. The default profile uses batch size 1, context length 32, hidden width 16, one layer, two heads, a 256 MiB training estimate budget, and a 1,536 MiB system-memory reserve. Estimates are admission guards, not guarantees. `job.json` records observed process RSS samples, not a claimed peak. `metrics.jsonl` contains measured step losses. Checkpoints are under the selected run's `checkpoints` directory. To resume, pass `--resume path\to\step-N.pt` with matching model settings and choose a fresh output directory; previous run records remain intact.

A previous tiny smoke run measured about 272 MiB of process RSS for a 904-parameter configuration. This is one measured sample including the Python/PyTorch runtime; it is not a prediction or guarantee for other machines/configurations.

Additional local commands:

```powershell
python -m neural_lab.cli dataset add --root neural_lab_data --file path\to\lesson.txt --provenance "User supplied" --license-note "Permission confirmed by user"
python -m neural_lab.cli dataset list --root neural_lab_data
python -m neural_lab.cli evaluate --checkpoint neural_lab_runs\first\checkpoints\step-10.pt --dataset path\to\held-out.txt
python -m neural_lab.cli generate --checkpoint neural_lab_runs\first\checkpoints\step-10.pt --prompt "Astrovox " --tokens 32 --top-k 8
python -m neural_lab.cli experiments --root neural_lab_runs
python -m neural_lab.cli models register --root neural_lab_runs --run-dir neural_lab_runs\first --name "First tiny experiment" --dataset-provenance "User-provided text"
```

Dataset deletion requires `dataset delete --confirm-delete`. The package's registry selection remains experimental metadata only; the integrated API additionally supports explicit experimental selection and rollback. Neither selection changes the default chat model.

## Authenticated dashboard integration

The FastAPI app includes `/neural-lab` routes authenticated with the existing Supabase token validator. Dataset and job/model metadata are stored in new RLS-protected Supabase tables in `supabase/migrations/20261016000000_neural_lab.sql`; dataset text, JSON job records, metrics, and checkpoints are kept below `NEURAL_LAB_STORAGE_ROOT/<authenticated-user-id>/`. Set `NEURAL_LAB_STORAGE_ROOT` to a durable, access-controlled directory on the backend host. The default `./astrovox_neural_lab` is intended for a single local backend instance; it is not shared storage for multi-instance deployments.

Apply the new Supabase migration to the target project before opening the dashboard panel. It was added as a migration file but has not been applied to a live database from this workspace. The API uses existing RLS on each metadata table and adds the authenticated user ID filter to reads and mutations. Uploads accept only UTF-8 `.txt` and `.md`, stream to a temporary file in 64 KiB chunks, cap content at 16 MiB, validate and deduplicate it, and retain provenance/license metadata. Dataset deletion is confirmed in the UI and rejected while an in-process job uses the dataset.

The dashboard adds training configuration, measured loss and observed RSS, checkpoint names, registration of completed checkpoints, held-out loss evaluation, explicit experimental model selection, rollback, and a text-generation playground. Resume creates a new run from the previous run's latest checkpoint. Pause is not implemented. Training remains CPU-only and serialized by the existing process and OS locks. This integration expects one backend instance on a host with the configured persistent storage; multi-instance job coordination and shared artifact storage are not implemented.

Windows local dashboard setup (use two terminals):

```powershell
# Apply supabase/migrations/20261016000000_neural_lab.sql to the configured Supabase project first.
$env:NEURAL_LAB_STORAGE_ROOT = "C:\AstrovoxNeuralLab"
Set-Location .\02-Backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# In another terminal from the repository root; npm ci is needed if node_modules is absent.
npm run dev
```

The frontend uses the existing `VITE_API_URL` setting or the repository's `/api` proxy fallback and the existing Supabase sign-in session. Supply the Supabase URL and publishable/anon key through the project's normal environment configuration. The storage directory must remain accessible to the backend and should be backed up if checkpoints need to survive machine failure.

The integrated API tests cover unauthenticated read and mutation rejection, a bounded user-scoped upload, tenant-filtered lookup, and a tiny end-to-end API training job using a fake persistence client. The API training smoke is skipped when less than 512 MiB is available at test time to avoid competing with the user's low-memory machine; it passed once when enough memory was available. These tests do not replace a live Supabase RLS/migration test. The source migration must still be applied and verified against the configured Supabase project before using the UI. The frontend build could not be run in this checkout because `node_modules`/Vite are absent; no dependency installation was attempted. Do not load this model as Astrovox's default assistant: no production chat code path was changed.

## Remaining work and verified limits

- Full repository regression tests and a live Supabase integration test remain to be run.
- The desktop dashboard includes the main dataset/job/model lifecycle and measured text statistics. It does not include a subword tokenizer, model configuration editing, or a pause control.
- Dataset/model artifacts are local to one backend host. Multi-instance coordination, distributed queues, shared object storage, and job recovery after abrupt host loss are not complete. Resume is available when a valid checkpoint remains on disk.
- Pause is unsupported; cancellation is cooperative at training-step boundaries and saves a checkpoint.
- The existing Astrovox default LLM and chat inference path remain unchanged. Experimental selection affects only the `/neural-lab/generate` route and has an explicit rollback operation.
