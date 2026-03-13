from __future__ import annotations

from threading import Lock

from aiops.skills.registry import SkillRegistry
from aiops.skills_lib import (
    FAULT_DIAGNOSIS_SKILLS,
    PROMETHEUS_SKILLS,
    SECURITY_SKILLS,
    VICTORIALOGS_SKILLS,
)

_lock = Lock()
_registry: SkillRegistry | None = None
_builtin_registered = False


def get_global_skill_registry() -> SkillRegistry:
    global _registry, _builtin_registered
    if _registry is not None and _builtin_registered:
        return _registry

    with _lock:
        if _registry is None:
            _registry = SkillRegistry()

        if not _builtin_registered:
            _registry.bulk_register(PROMETHEUS_SKILLS)
            _registry.bulk_register(VICTORIALOGS_SKILLS)
            _registry.bulk_register(FAULT_DIAGNOSIS_SKILLS)
            _registry.bulk_register(SECURITY_SKILLS)
            _builtin_registered = True

        return _registry


def _reset_global_skill_registry_for_tests() -> None:
    global _registry, _builtin_registered
    with _lock:
        _registry = None
        _builtin_registered = False
