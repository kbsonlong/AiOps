# Skills Deployment Guide

## Prerequisites

- Python environment configured for the project.
- `AIOPS_SKILLS__BASE_DIR` set if you do not want the default `~/.aiops`.

## Initialize Directories

```bash
scripts/deploy_skills.sh
```

This creates:
- `${AIOPS_SKILLS__BASE_DIR}/skills`
- `${AIOPS_SKILLS__BASE_DIR}/cache`
- `${AIOPS_SKILLS__BASE_DIR}/logs`

## Backup Skills

```bash
scripts/backup_skills.sh /path/to/backups
```

## Verify

Run tests:

```bash
.venv/bin/python -m unittest discover -s tests -p "test*.py"
```

## Rollback

Extract a backup archive into the skills base directory:

```bash
tar -xzf /path/to/skills_backup_YYYYMMDD_HHMMSS.tar.gz -C "${AIOPS_SKILLS__BASE_DIR}"
```
