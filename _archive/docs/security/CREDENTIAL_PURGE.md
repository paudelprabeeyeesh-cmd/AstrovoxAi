# AstrovoxAi Credential Purge & Git History Remediation

## Overview

This document provides the operational procedure for purging all sensitive credentials from the AstrovoxAi git history. The procedure is implemented in `scripts/purge_secrets.sh`.

## Current Exposure Status (as of initial audit)

| Project | Endpoint | Status |
|---------|----------|--------|
| Supabase Project 1 | `***REMOVED***.supabase.co` | **EXPOSED** — anon key in git history |
| Supabase Project 2 | `dowinoownpxfmowxltuw.supabase.co` | **EXPOSED** — anon key in `src/supabase.js` |

## Prerequisites

1. Install git-filter-repo:
   ```bash
   pip install git-filter-repo
   ```

2. Install gitleaks (for CI):
   ```bash
   # macOS
   brew install gitleaks
   # Linux
   wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_amd64.tar.gz
   tar -xzf gitleaks_8.18.0_linux_amd64.tar.gz
   sudo mv gitleaks /usr/local/bin/
   ```

3. Notify all team members. They will need to re-clone the repository after the purge.

## Execution Procedure

### Option A: Use the Automated Script

```bash
chmod +x scripts/purge_secrets.sh
./scripts/purge_secrets.sh
```

The script will:
1. Create a backup branch
2. Remove `.env*` files from history
3. Scrub secret patterns from remaining files
4. Install gitleaks pre-commit hook
5. Verify no `.env` files are tracked
6. Update `.gitignore`
7. Run second-pass inline secret filter
8. Force-push cleaned history (with confirmation)

### Option B: Manual Procedure

#### Step 1: Install git-filter-repo

```bash
pip install git-filter-repo
```

#### Step 2: Backup

```bash
git branch backup/pre-credential-purge
git tag backup/pre-credential-purge-$(date +%Y%m%d-%H%M%S)
```

#### Step 3: Remove .env files from history

```bash
git filter-repo --invert-paths \
    --path .env \
    --path .env.local \
    --path .env.production \
    --path .env.staging \
    --path .env.development \
    --path backend/.env \
    --force
```

#### Step 4: Scrub inline secrets

Create `scripts/secret_callback.py`:
```python
import re

SECRET_PATTERNS = [
    (r'AKIA[0-9A-Z]{16}', '[REDACTED-aws_key]'),
    (r'ghp_[A-Za-z0-9]{30,}', '[REDACTED-github_token]'),
    (r'gho_[A-Za-z0-9]{30,}', '[REDACTED-github_token]'),
    (r'xoxb-[0-9A-Za-z-]{10,}', '[REDACTED-slack_token]'),
    (r'sk-[A-Za-z0-9]{20,}', '[REDACTED-openai_key]'),
    (r'sk_live_[A-Za-z0-9]{20,}', '[REDACTED-stripe_key]'),
    (r'***REMOVED***', '[REDACTED-supabase-project]'),
    (r'dowinoownpxfmowxltuw', '[REDACTED-supabase-project]'),
    (r'sb_publishable_[A-Za-z0-9_]+', '[REDACTED-supabase-key]'),
]


def blob_callback(blob):
    try:
        content = blob.data.decode('utf-8', errors='ignore')
    except Exception:
        return blob.data
    for pattern, replacement in SECRET_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content.encode('utf-8')
```

Run the filter:
```bash
git filter-repo --blob-callback "$(cat scripts/secret_callback.py)" --force
```

#### Step 5: Update .gitignore

```bash
cat >> .gitignore << 'EOF'

# Environment files
.env
.env.*
!.env.example
EOF
```

#### Step 6: Add pre-commit hook

Create `.git/hooks/pre-commit`:
```bash
#!/usr/bin/env bash
if command -v gitleaks >/dev/null 2>&1; then
    gitleaks protect --staged --no-banner
    if [ $? -ne 0 ]; then
        echo "Gitleaks detected secrets. Commit aborted."
        exit 1
    fi
fi
```

```bash
chmod +x .git/hooks/pre-commit
```

#### Step 7: Force-push

```bash
git push origin --force --all
git push origin --force --tags
```

## Post-Purge Actions

### Immediate: Rotate All Exposed Credentials

| Service | Rotation Action |
|---------|-----------------|
| Supabase Project 1 | Settings → API → Reset anon key |
| Supabase Project 2 | Settings → API → Reset anon key |
| OpenAI | https://platform.openai.com/api-keys → Revoke + Create |
| GitHub | Settings → Developer settings → Revoke PAT |
| Stripe | Dashboard → API keys → Roll |
| Slack | App settings → Regenerate tokens |

### Update .env.example

```bash
# After rotation, populate .env.example with placeholders
cat > .env.example << 'EOF'
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=sk-your-key

# JWT
JWT_SECRET=generate-a-strong-random-secret
JWT_EXPIRES_IN=3600
EOF
```

### Verify the Purge

```bash
# Search for old commit content
git log --all --full-history -p | grep -E "***REMOVED***|dowinoownpxfmowxltuw" | head -5

# If any results appear, run the purge again
```

### CI Integration

Add to `.github/workflows/secret-scan.yml`:
```yaml
name: Secret Scan

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Team Communication

Send this to all team members:

> **Subject: URGENT: Repository Re-clone Required**
>
> We've purged sensitive credentials from the git history. The remote
> repository has been force-pushed.
>
> **Action required:**
> 1. Re-clone the repository (do not pull, RE-CLONE):
>    `git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git`
> 2. Discard any local branches with old history
> 3. Update your local `.env` files with newly rotated credentials
> 4. Verify gitleaks is installed locally for pre-commit scanning

## References

- git-filter-repo: https://github.com/newren/git-filter-repo
- gitleaks: https://github.com/gitleaks/gitleaks
- GitHub: Removing sensitive data from a repository
- Supabase: Rotating API keys
