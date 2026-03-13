#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${AIOPS_SKILLS__BASE_DIR:-$HOME/.aiops}"
BACKUP_DIR="${1:-$PWD/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE="${BACKUP_DIR}/skills_backup_${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

tar -czf "${ARCHIVE}" -C "${BASE_DIR}" skills cache logs

echo "Backup created: ${ARCHIVE}"
