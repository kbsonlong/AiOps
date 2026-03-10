from __future__ import annotations

import argparse
import json

from aiops.skills import SkillDiscoveryService, SkillRegistry
from aiops.skills_lib import (
    FAULT_DIAGNOSIS_SKILLS,
    PROMETHEUS_SKILLS,
    SECURITY_SKILLS,
    VICTORIALOGS_SKILLS,
)


def _build_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.bulk_register(PROMETHEUS_SKILLS)
    registry.bulk_register(VICTORIALOGS_SKILLS)
    registry.bulk_register(FAULT_DIAGNOSIS_SKILLS)
    registry.bulk_register(SECURITY_SKILLS)
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all skills")

    discover = sub.add_parser("discover", help="Discover skills")
    discover.add_argument("--query", required=True)
    discover.add_argument("--tag", action="append", default=[])

    args = parser.parse_args()
    registry = _build_registry()

    if args.command == "list":
        print(json.dumps([s.model_dump() for s in registry.all()], ensure_ascii=False, indent=2))
        return

    if args.command == "discover":
        discovery = SkillDiscoveryService(registry=registry)
        skills = discovery.discover_skills(args.query, tags=args.tag or None)
        print(json.dumps([s.model_dump() for s in skills], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
