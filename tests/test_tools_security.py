import unittest

from aiops.tools.security_tools import (
    assess_compliance,
    audit_access_logs,
    check_security_config,
    detect_security_threats,
    scan_vulnerabilities,
)


class TestSecurityTools(unittest.TestCase):
    def test_scan_vulnerabilities(self) -> None:
        result = scan_vulnerabilities("localhost")
        self.assertEqual(result["target"], "localhost")

    def test_check_security_config(self) -> None:
        result = check_security_config("ssh")
        self.assertEqual(result["config_type"], "ssh")

    def test_audit_access_logs(self) -> None:
        result = audit_access_logs(user="root")
        self.assertIn("keyword", result)

    def test_detect_security_threats(self) -> None:
        result = detect_security_threats(["Failed password for root"], {"network_packets": 1})
        self.assertEqual(result["threat"], "brute_force")

    def test_assess_compliance(self) -> None:
        result = assess_compliance()
        self.assertEqual(result["status"], "partial")


if __name__ == "__main__":
    unittest.main(verbosity=2)

