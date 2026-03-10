import unittest
from unittest.mock import Mock, patch

from aiops.tools.metrics_tools import (
    collect_cpu_metrics,
    collect_disk_metrics,
    collect_memory_metrics,
    collect_network_metrics,
    detect_metric_anomaly,
    query_prometheus,
)


class TestMetricsTools(unittest.TestCase):
    @patch("aiops.tools.metrics_tools.urlopen")
    def test_collect_cpu_metrics(self, urlopen_mock: Mock) -> None:
        response = Mock()
        response.read.return_value = b'{"status":"success","data":{"result":[{"value":[0,"12.5"]}]}}'
        urlopen_mock.return_value.__enter__.return_value = response
        result = collect_cpu_metrics(base_url="http://localhost:9090")
        self.assertEqual(result["cpu_percent"], 12.5)

    @patch("aiops.tools.metrics_tools.urlopen")
    def test_collect_memory_metrics(self, urlopen_mock: Mock) -> None:
        response = Mock()
        response.read.return_value = b'{"status":"success","data":{"result":[{"value":[0,"55.0"]}]}}'
        urlopen_mock.return_value.__enter__.return_value = response
        result = collect_memory_metrics(base_url="http://localhost:9090")
        self.assertEqual(result["memory_percent"], 55.0)

    @patch("aiops.tools.metrics_tools.urlopen")
    def test_collect_disk_metrics(self, urlopen_mock: Mock) -> None:
        response = Mock()
        response.read.return_value = b'{"status":"success","data":{"result":[{"value":[0,"70.0"]}]}}'
        urlopen_mock.return_value.__enter__.return_value = response
        result = collect_disk_metrics(base_url="http://localhost:9090")
        self.assertEqual(result["disk_percent"], 70.0)

    @patch("aiops.tools.metrics_tools.urlopen")
    def test_collect_network_metrics(self, urlopen_mock: Mock) -> None:
        response_recv = Mock()
        response_recv.read.return_value = b'{"status":"success","data":{"result":[{"value":[0,"100"]}]}}'
        response_sent = Mock()
        response_sent.read.return_value = b'{"status":"success","data":{"result":[{"value":[0,"200"]}]}}'
        urlopen_mock.return_value.__enter__.side_effect = [response_recv, response_sent]
        result = collect_network_metrics(base_url="http://localhost:9090")
        self.assertEqual(result["bytes_recv_per_sec"], 100.0)
        self.assertEqual(result["bytes_sent_per_sec"], 200.0)

    def test_detect_metric_anomaly(self) -> None:
        result = detect_metric_anomaly(90, 80)
        self.assertTrue(result["is_anomaly"])

    @patch("aiops.tools.metrics_tools.urlopen")
    def test_query_prometheus(self, urlopen_mock: Mock) -> None:
        response = Mock()
        response.read.return_value = b'{"status":"success","data":{"result":[]}}'
        urlopen_mock.return_value.__enter__.return_value = response
        result = query_prometheus("up", base_url="http://localhost:9090", timeout=1.0)
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main(verbosity=2)

