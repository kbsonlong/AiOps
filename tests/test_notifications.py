import unittest

from aiops.notifications.templates import format_report
from aiops.utils.formatters import redact_secrets


class TestNotifications(unittest.TestCase):
    def test_redact_secrets(self) -> None:
        text = "api_key=SECRET123 token=ABCDEF123"
        redacted = redact_secrets(text)
        self.assertNotIn("SECRET123", redacted)
        self.assertIn("api_key=***", redacted)

    def test_format_report(self) -> None:
        report = format_report(
            "check",
            [{"source": "metrics", "result": "api_key=SECRET123"}],
        )
        self.assertIn("Query: check", report)
        self.assertIn("metrics", report)
        self.assertIn("api_key=***", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)

