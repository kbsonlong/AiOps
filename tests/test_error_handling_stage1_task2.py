import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from aiops.api.skill_api import app, permission_checker
from aiops.skills.exceptions import SkillExistsError
from aiops.workflows.router_workflow import classify_query


class TestErrorHandlingStage1Task2(unittest.TestCase):
    def test_classify_query_fallback_returns_safe_classification(self) -> None:
        result = classify_query({"query": "hello"}, router_llm=None)
        self.assertIn("classifications", result)
        self.assertTrue(result["classifications"])
        self.assertEqual(result["classifications"][0]["source"], "knowledge_base")

    def test_api_returns_403_without_leaking_details(self) -> None:
        client = TestClient(app)
        original = permission_checker.allow_create
        try:
            permission_checker.allow_create = False
            resp = client.post(
                "/skills/create",
                json={
                    "name": "demo",
                    "content": "content",
                    "category": "custom",
                    "description": "",
                    "author": None,
                    "risk_level": "medium",
                    "tags": [],
                },
            )
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(resp.json()["detail"], "无权限执行该操作")
        finally:
            permission_checker.allow_create = original

    def test_api_returns_400_with_safe_detail(self) -> None:
        client = TestClient(app)
        with patch("aiops.api.skill_api.SkillManager") as mocked_manager:
            mocked_manager.return_value.create_skill.side_effect = SkillExistsError("SECRET_TOKEN=abc")
            resp = client.post(
                "/skills/create",
                json={
                    "name": "demo",
                    "content": "content",
                    "category": "custom",
                    "description": "",
                    "author": None,
                    "risk_level": "medium",
                    "tags": [],
                },
            )
        self.assertEqual(resp.status_code, 400)
        payload = resp.json()
        self.assertEqual(payload["detail"], "技能已存在")
        self.assertNotIn("SECRET_TOKEN", payload["detail"])

    def test_api_returns_500_with_generic_message(self) -> None:
        client = TestClient(app)
        with patch("aiops.api.skill_api.SkillManager") as mocked_manager:
            mocked_manager.return_value.create_skill.side_effect = RuntimeError("SECRET_TOKEN=abc")
            resp = client.post(
                "/skills/create",
                json={
                    "name": "demo",
                    "content": "content",
                    "category": "custom",
                    "description": "",
                    "author": None,
                    "risk_level": "medium",
                    "tags": [],
                },
            )
        self.assertEqual(resp.status_code, 500)
        payload = resp.json()
        self.assertEqual(payload["detail"], "内部错误，请稍后重试")
        self.assertNotIn("SECRET_TOKEN", payload["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
