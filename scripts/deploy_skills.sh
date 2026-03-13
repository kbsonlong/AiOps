#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${AIOPS_SKILLS__BASE_DIR:-$HOME/.aiops}"
SKILLS_DIR="${BASE_DIR}/skills"
CACHE_DIR="${BASE_DIR}/cache"
LOGS_DIR="${BASE_DIR}/logs"

mkdir -p "${SKILLS_DIR}" "${CACHE_DIR}" "${LOGS_DIR}"
touch "${SKILLS_DIR}/.index.json"

echo "Skills directories initialized at ${BASE_DIR}"
