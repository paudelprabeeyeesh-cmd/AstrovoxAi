#!/usr/bin/env bash
# ============================================================================
# AstrovoxAi Credential Sanitization & Git History Purge
# ============================================================================
# Purpose: Remove all sensitive credentials (.env files, API keys, tokens)
#          from the entire git history and force-push the cleaned history.
#
# WARNING: This rewrites git history. Coordinate with all collaborators.
#          All clones must be re-cloned after this operation.
# ============================================================================

set -euo pipefail

# ---- Pre-flight checks ----------------------------------------------------

if ! command -v git-filter-repo >/dev/null 2>&1; then
    echo "ERROR: git-filter-repo is not installed."
    echo "Install with: pip install git-filter-repo"
    exit 1
fi

# Confirm current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Verify remote
REMOTE_URL=$(git config --get remote.origin.url || echo "")
if [ -z "$REMOTE_URL" ]; then
    echo "ERROR: no remote configured."
    exit 1
fi
echo "Remote: $REMOTE_URL"

# ---- Step 1: Backup current state ---------------------------------------

echo "[1/8] Creating backup branch..."
git branch backup/pre-credential-purge 2>/dev/null || true

# ---- Step 2: Remove .env files from history -----------------------------

echo "[2/8] Purging .env files from history..."
git filter-repo --invert-paths \
    --path .env \
    --path .env.local \
    --path .env.production \
    --path .env.staging \
    --path .env.development \
    --path backend/.env \
    --path .env.example \
    --force 2>&1 | head -20

# ---- Step 3: Scrub secrets from all remaining files -------------------

echo "[3/8] Scanning for credential patterns in remaining files..."

# Patterns to scrub
SCRUB_PATTERNS=(
    'AKIA[0-9A-Z]{16}'
    'ghp_[A-Za-z0-9]{30,}'
    'gho_[A-Za-z0-9]{30,}'
    'xoxb-[0-9A-Za-z-]{10,}'
    'sk-[A-Za-z0-9]{20,}'
    'sk_live_[A-Za-z0-9]{20,}'
    '***REMOVED***'
    'dowinoownpxfmowxltuw'
    'sb_publishable_[A-Za-z0-9_]+'
)

for pattern in "${SCRUB_PATTERNS[@]}"; do
    # Replace in all text files
    find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.tsx" -o -name "*.jsx" -o -name "*.json" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.txt" -o -name "*.sh" -o -name "*.env*" \) \
        -not -path "*/node_modules/*" \
        -not -path "*/.venv/*" \
        -not -path "*/venv/*" \
        -not -path "*/.git/*" \
        -not -path "*/dist/*" \
        -not -path "*/build/*" \
        -exec grep -lE "$pattern" {} + 2>/dev/null | while read -r f; do
        echo "  Scrubbing: $f"
        sed -i.bak -E "s/$pattern/[REDACTED-CREDENTIAL]/g" "$f"
        rm -f "$f.bak"
    done
done

# ---- Step 4: Add gitleaks pre-commit hook -------------------------------

echo "[4/8] Installing gitleaks pre-commit hook..."

mkdir -p .git/hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/usr/bin/env bash
# Gitleaks pre-commit hook
if command -v gitleaks >/dev/null 2>&1; then
    gitleaks protect --staged --no-banner
    if [ $? -ne 0 ]; then
        echo "Gitleaks detected secrets. Commit aborted."
        exit 1
    fi
fi
EOF
chmod +x .git/hooks/pre-commit

# ---- Step 5: Verify .env files no longer tracked ----------------------

echo "[5/8] Verifying .env files are removed..."
if git ls-files | grep -E '\.env$|\.env\.' | grep -v '.env.example'; then
    echo "ERROR: .env files still tracked!"
    exit 1
fi
echo "  .env files: not tracked ✓"

# ---- Step 6: Add .env to .gitignore ------------------------------------

echo "[6/8] Updating .gitignore..."
if [ -f .gitignore ]; then
    if ! grep -q "^\.env$" .gitignore; then
        echo ".env" >> .gitignore
        echo ".env.*" >> .gitignore
        echo "!.env.example" >> .gitignore
    fi
fi

# ---- Step 7: Run history filter to scrub inline secrets ----------------

echo "[7/8] Running second-pass history filter..."

# Use --blob-callback to replace sensitive strings in all blobs
SECRET_PATTERNS=(
    's/(AKIA[0-9A-Z]{16})/[REDACTED-aws_key]/g'
    's/(ghp_[A-Za-z0-9]{30,})/[REDACTED-github_token]/g'
    's/(xoxb-[0-9A-Za-z-]{10,})/[REDACTED-slack_token]/g'
    's/(sk-[A-Za-z0-9]{20,})/[REDACTED-openai_key]/g'
    's/(sk_live_[A-Za-z0-9]{20,})/[REDACTED-stripe_key]/g'
    's/(***REMOVED***)/[REDACTED-supabase-project]/g'
    's/(dowinoownpxfmowxltuw)/[REDACTED-supabase-project]/g'
)

# Build sed command
SED_EXPR=$(printf "%s;" "${SECRET_PATTERNS[@]}")

git filter-repo --blob-callback "
    import re
    content = blob.data.decode('utf-8', errors='ignore')
    content = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED-aws_key]', content)
    content = re.sub(r'ghp_[A-Za-z0-9]{30,}', '[REDACTED-github_token]', content)
    content = re.sub(r'xoxb-[0-9A-Za-z-]{10,}', '[REDACTED-slack_token]', content)
    content = re.sub(r'sk-[A-Za-z0-9]{20,}', '[REDACTED-openai_key]', content)
    content = re.sub(r'sk_live_[A-Za-z0-9]{20,}', '[REDACTED-stripe_key]', content)
    content = re.sub(r'***REMOVED***', '[REDACTED-supabase-project]', content)
    content = re.sub(r'dowinoownpxfmowxltuw', '[REDACTED-supabase-project]', content)
    return content.encode('utf-8')
" --force 2>&1 | head -10

# ---- Step 8: Force-push to remote --------------------------------------

echo "[8/8] Force-pushing cleaned history to remote..."
echo ""
echo "==================================================================="
echo "  CRITICAL: This will rewrite the remote git history!"
echo "  All collaborators must re-clone the repository after this."
echo "==================================================================="
echo ""
read -p "Type 'YES I UNDERSTAND' to continue: " confirm

if [ "$confirm" = "YES I UNDERSTAND" ]; then
    git push origin --force --all
    git push origin --force --tags
    echo ""
    echo "✓ Credential purge complete."
    echo ""
    echo "NEXT STEPS:"
    echo "  1. Rotate ALL exposed credentials immediately:"
    echo "     - Supabase project 1 (***REMOVED***): reset anon key"
    echo "     - Supabase project 2 (dowinoownpxfmowxltuw): reset anon key"
    echo "     - OpenAI API keys: rotate in dashboard"
    echo "     - GitHub PATs: revoke and re-issue"
    echo "  2. Notify all team members to re-clone the repository"
    echo "  3. Run a fresh audit to confirm no remaining leaks"
else
    echo "Aborted. Run the script again when ready."
    exit 0
fi
