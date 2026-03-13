import os
import tempfile
import time
import unittest
from pathlib import Path

from aiops.config import ConfigManager, load_settings
from aiops.config.validator import validate_settings


class TestConfig(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_defaults(self) -> None:
        settings = load_settings()
        self.assertEqual(settings.app_name, "aiops-agent")
        self.assertEqual(settings.environment, "dev")
        self.assertEqual(settings.metrics.cpu_threshold, 80.0)
        self.assertEqual(settings.knowledge.vector_store.collection_name, "knowledge_base")

    def test_yaml_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.yaml"
            path.write_text(
                "app_name: aiops-test\n"
                "metrics:\n"
                "  cpu_threshold: 90\n"
                "logs:\n"
                "  max_lines: 300\n",
                encoding="utf-8",
            )
            settings = load_settings(path)
            self.assertEqual(settings.app_name, "aiops-test")
            self.assertEqual(settings.metrics.cpu_threshold, 90.0)
            self.assertEqual(settings.logs.max_lines, 300)

    def test_env_override(self) -> None:
        os.environ["AIOPS_METRICS__CPU_THRESHOLD"] = "85"
        settings = load_settings()
        self.assertEqual(settings.metrics.cpu_threshold, 85.0)

    def test_knowledge_env_override(self) -> None:
        os.environ["AIOPS_KNOWLEDGE__EMBEDDINGS__MODEL"] = "ollama/nomic-embed-text:v2"
        os.environ["AIOPS_KNOWLEDGE__VECTOR_STORE__PERSIST_DIRECTORY"] = "./tmp_chroma"
        settings = load_settings()
        self.assertEqual(settings.knowledge.embeddings.model, "ollama/nomic-embed-text:v2")
        self.assertEqual(settings.knowledge.vector_store.persist_directory, "./tmp_chroma")

    def test_config_manager_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.yaml"
            path.write_text("app_name: aiops-test\n", encoding="utf-8")
            manager = ConfigManager(path)
            self.assertEqual(manager.settings.app_name, "aiops-test")
            time.sleep(0.01)
            path.write_text("app_name: aiops-reload\n", encoding="utf-8")
            self.assertTrue(manager.check_reload())
            self.assertEqual(manager.settings.app_name, "aiops-reload")

    def test_validate_settings_success(self) -> None:
        settings = load_settings()
        result = validate_settings(settings)
        self.assertTrue(result.valid)
        self.assertEqual(result.issues, [])

    def test_validate_settings_fails_on_empty_url(self) -> None:
        os.environ["AIOPS_METRICS__PROMETHEUS_BASE_URL"] = ""
        settings = load_settings()
        result = validate_settings(settings)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.path == "metrics.prometheus_base_url" for issue in result.issues))

    def test_validate_settings_fails_on_non_http_url(self) -> None:
        os.environ["AIOPS_LOGS__VICTORIALOGS_BASE_URL"] = "ftp://victorialogs:9428"
        settings = load_settings()
        result = validate_settings(settings)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.path == "logs.victorialogs_base_url" for issue in result.issues))


if __name__ == "__main__":
    unittest.main(verbosity=2)
