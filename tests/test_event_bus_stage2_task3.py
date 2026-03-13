import time
import unittest

from aiops.core.events import Event, EventBus


class TestEventBusStage2Task3(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.bus = EventBus()
        await self.bus.start()

    async def asyncTearDown(self) -> None:
        await self.bus.stop()

    async def test_publish_subscribe(self) -> None:
        received: list[str] = []

        def handler_sync(event: Event) -> None:
            received.append(f"sync:{event.source}")

        async def handler_async(event: Event) -> None:
            received.append(f"async:{event.source}")

        self.bus.subscribe(Event, handler_sync)
        self.bus.subscribe(Event, handler_async)

        await self.bus.publish(Event(timestamp=time.time(), source="test"))
        await self.bus.join()

        self.assertEqual(set(received), {"sync:test", "async:test"})

    async def test_handler_exception_isolated(self) -> None:
        received: list[str] = []

        def bad_handler(event: Event) -> None:
            received.append("bad:called")
            raise RuntimeError("boom")

        def good_handler(event: Event) -> None:
            received.append(f"good:{event.source}")

        self.bus.subscribe(Event, bad_handler)
        self.bus.subscribe(Event, good_handler)

        await self.bus.publish(Event(timestamp=time.time(), source="evt1"))
        await self.bus.publish(Event(timestamp=time.time(), source="evt2"))
        await self.bus.join()

        self.assertIn("bad:called", received)
        self.assertIn("good:evt1", received)
        self.assertIn("good:evt2", received)


if __name__ == "__main__":
    unittest.main(verbosity=2)

