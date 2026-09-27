#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PYTHON:-python3}"
CONFIG="${CONFIG:-${REPO_ROOT}/configs/versioned/config_phase1_v1.yaml}"

echo "============================================================"
echo "Phase J Reproducibility Package - Bash Wrapper"
echo "============================================================"

cd "${REPO_ROOT}"

echo "[repro] Using Python: ${PYTHON}"
echo "[repro] Repo root:   ${REPO_ROOT}"
echo "[repro] Config:      ${CONFIG}"

if [[ ! -f "${CONFIG}" ]]; then
    echo "ERROR: Config file not found: ${CONFIG}"
    exit 1
fi

"${PYTHON}" "${SCRIPT_DIR}/reproduce.py" --config "${CONFIG}" "$@"
