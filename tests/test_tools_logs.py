import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from aiops.tools.logs_tools import (
    analyze_log_patterns,
    collect_system_logs,
    correlate_log_events,
    detect_log_anomalies,
    query_victorialogs,
    search_logs,
)


class TestLogsTools(unittest.TestCase):
    def test_collect_and_search_logs_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "INFO startup\nERROR failed to connect\nWARN retry\n",
                encoding="utf-8",
            )
            collected = collect_system_logs(str(path), lines=10)
            self.assertIn("ERROR", collected)
            results = search_logs("failed", log_type=str(path), lines=10)
            self.assertEqual(len(results), 1)

    def test_analyze_patterns(self) -> None:
        text = "INFO ok\nERROR failed\nWARN slow\n"
        counts = analyze_log_patterns(text)
        self.assertEqual(counts["info"], 1)
        self.assertEqual(counts["error"], 1)

    def test_detect_anomalies(self) -> None:
        text = "\n".join(["ERROR crash"] * 5)
        result = detect_log_anomalies(text)
        self.assertTrue(result["is_anomaly"])

    def test_correlate(self) -> None:
        events = ["User 123 logged in", "User 456 logged in", "Disk 1 full"]
        result = correlate_log_events(events)
        self.assertGreaterEqual(result["unique_event_count"], 2)

    @patch("aiops.tools.logs_tools.urlopen")
    def test_query_victorialogs(self, urlopen_mock) -> None:
        response = Mock()
        response.read.return_value = b'{"status":"success","data":[]}'
        urlopen_mock.return_value.__enter__.return_value = response
        result = query_victorialogs("error", base_url="http://localhost:9428", limit=10)
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main(verbosity=2)
