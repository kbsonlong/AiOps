import unittest
from datetime import datetime, timezone
from pathlib import Path

from aiops.skills.models import SkillCategory, SkillDefinition, SkillRiskLevel
from aiops.skills.user_models import QualityScore, ScanResult, UserSkill, UserSkillMetadata


class TestUserModels(unittest.TestCase):
    def test_user_skill_to_dict(self) -> None:
        skill_def = SkillDefinition(
            id="monitoring-test-skill",
            name="Test Skill",
            description="test",
            category=SkillCategory.MONITORING,
            tags=["a"],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            risk_level=SkillRiskLevel.LOW,
            implementation_type="user_skill",
            implementation_ref="~/.aiops/skills/monitoring-test-skill/SKILL.md",
        )
        metadata = UserSkillMetadata(
            skill_id=skill_def.id,
            file_path=Path("/tmp/skill/SKILL.md"),
            created_by="tester",
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            quality_score=QualityScore(overall=0.9, category_scores={"x": 1.0}, recommendations=[]),
            security_scan=ScanResult(risk_level="safe", issues=[], summary="ok"),
        )
        user_skill = UserSkill(skill_id=skill_def.id, definition=skill_def, metadata=metadata)
        payload = user_skill.to_dict()
        self.assertEqual(payload["id"], skill_def.id)
        self.assertEqual(payload["skill_type"], "user_created")
        self.assertEqual(payload["file_path"], str(metadata.file_path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
