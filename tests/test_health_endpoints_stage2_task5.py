import importlib.util
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from fastapi.responses import JSONResponse

from aiops.api.skill_api import health, ready


class TestHealthEndpointsStage2Task5(unittest.TestCase):
    def test_health_and_ready_do_not_probe_external_connectivity(self) -> None:
        patches: list = [
            patch(
                "socket.create_connection",
                side_effect=AssertionError("health endpoints must not call socket.create_connection"),
            ),
            patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("health endpoints must not call urllib.request.urlopen"),
            ),
        ]

        if importlib.util.find_spec("httpx") is not None:
            patches.extend(
                [
                    patch(
                        "httpx.request",
                        side_effect=AssertionError("health endpoints must not call httpx.request"),
                    ),
                    patch(
                        "httpx.Client.request",
                        side_effect=AssertionError("health endpoints must not call httpx.Client.request"),
                    ),
                ]
            )

        if importlib.util.find_spec("aiohttp") is not None:
            patches.append(
                patch(
                    "aiohttp.ClientSession._request",
                    side_effect=AssertionError("health endpoints must not call aiohttp.ClientSession._request"),
                )
            )

        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            health_payload = health()
            self.assertIsInstance(health_payload, dict)
            self.assertIn(health_payload.get("status"), ("healthy", "unhealthy"))

            ready_payload = ready()
            if isinstance(ready_payload, JSONResponse):
                self.assertEqual(ready_payload.status_code, 503)
            else:
                self.assertIsInstance(ready_payload, dict)
                self.assertIn(ready_payload.get("status"), ("healthy", "unhealthy"))

            for mock_obj in mocks:
                self.assertFalse(mock_obj.called)


if __name__ == "__main__":
    unittest.main()
