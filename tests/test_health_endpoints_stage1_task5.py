import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from aiops.api.skill_api import app
from aiops.config.validator import ValidationIssue, ValidationResult


class TestHealthEndpointsStage1Task5(unittest.TestCase):
    def test_health_and_ready_healthy(self) -> None:
        client = TestClient(app)
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        payload = health.json()
        self.assertEqual(payload["status"], "healthy")
        self.assertIn("config", payload["checks"])

        ready = client.get("/ready")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "healthy")

    @patch("aiops.health.checker.validate_settings")
    def test_ready_returns_503_when_unhealthy(self, validate_settings_mock) -> None:
        validate_settings_mock.return_value = ValidationResult(
            valid=False,
            issues=[ValidationIssue(path="test", message="invalid")],
        )
        client = TestClient(app)
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        payload = health.json()
        self.assertEqual(payload["status"], "unhealthy")
        self.assertEqual(payload["checks"]["config"]["status"], "unhealthy")

        ready = client.get("/ready")
        self.assertEqual(ready.status_code, 503)
        self.assertEqual(ready.json()["status"], "unhealthy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
