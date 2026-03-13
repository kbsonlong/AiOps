from __future__ import annotations

import argparse
import json
from pathlib import Path

from aiops.skills.manager import SkillManager

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
    sub.add_parser("list-user", help="List user skills")

    discover = sub.add_parser("discover", help="Discover skills")
    discover.add_argument("--query", required=True)
    discover.add_argument("--tag", action="append", default=[])

    create = sub.add_parser("create", help="Create a new user skill")
    create.add_argument("--name", required=True)
    create.add_argument("--category", default="custom")
    create.add_argument("--description", default="")
    create.add_argument("--author", default=None)
    create.add_argument("--risk-level", default="medium")
    create.add_argument("--tag", action="append", default=[])
    create.add_argument("--content-file", required=True, help="Path to a markdown file containing skill content")

    scan = sub.add_parser("scan", help="Rescan a user skill for security")
    scan.add_argument("skill_id")

    quality = sub.add_parser("quality", help="Get skill quality report")
    quality.add_argument("skill_id")

    args = parser.parse_args()
    registry = _build_registry()

    if args.command == "list":
        print(json.dumps([s.model_dump() for s in registry.all()], ensure_ascii=False, indent=2))
        return

    if args.command == "list-user":
        manager = SkillManager()
        print(json.dumps(manager.list_user_skills(), ensure_ascii=False, indent=2))
        return

    if args.command == "discover":
        discovery = SkillDiscoveryService(registry=registry)
        skills = discovery.discover_skills(args.query, tags=args.tag or None)
        print(json.dumps([s.model_dump() for s in skills], ensure_ascii=False, indent=2))
        return

    if args.command == "create":
        content_path = Path(args.content_file)
        content = content_path.read_text(encoding="utf-8")
        manager = SkillManager()
        user_skill = manager.create_skill(
            name=args.name,
            content=content,
            category=args.category,
            metadata={
                "description": args.description,
                "author": args.author,
                "risk_level": args.risk_level,
                "tags": args.tag,
            },
        )
        print(json.dumps(user_skill.to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "scan":
        manager = SkillManager()
        result = manager.scan_skill(args.skill_id)
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        return

    if args.command == "quality":
        manager = SkillManager()
        score = manager.evaluate_quality(args.skill_id)
        print(json.dumps(score.model_dump(), ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
