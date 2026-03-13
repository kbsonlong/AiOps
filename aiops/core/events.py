from __future__ import annotations

import asyncio
import threading
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, List, Optional, Type, TypeVar

from aiops.core.error_handler import get_logger

logger = get_logger(__name__)

TEvent = TypeVar("TEvent", bound="Event")
EventHandler = Callable[[TEvent], Any] | Callable[[TEvent], Awaitable[Any]]


@dataclass(slots=True)
class Event:
    timestamp: float
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.__class__.__name__, "timestamp": self.timestamp, "source": self.source}


@dataclass(slots=True)
class SkillExecutionEvent(Event):
    skill_id: str
    duration_ms: int
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "skill_id": self.skill_id,
                "duration_ms": self.duration_ms,
                "success": self.success,
                "error": self.error,
            }
        )
        return payload


class EventBus:
    def __init__(self) -> None:
        self._listeners: DefaultDict[Type[Event], List[EventHandler]] = defaultdict(list)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue[Event]] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._thread: Optional[threading.Thread] = None
        self._thread_ready = threading.Event()

    def subscribe(self, event_type: Type[TEvent], handler: EventHandler[TEvent]) -> Callable[[], None]:
        self._listeners[event_type].append(handler)

        def unsubscribe() -> None:
            handlers = self._listeners.get(event_type)
            if not handlers:
                return
            try:
                handlers.remove(handler)
            except ValueError:
                return

        return unsubscribe

    async def start(self) -> None:
        if self._loop is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self._process_loop())

    def start_background(self) -> None:
        if self._loop is not None:
            return

        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._queue = asyncio.Queue()
            self._task = loop.create_task(self._process_loop())
            self._thread_ready.set()
            try:
                loop.run_forever()
            finally:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()

        self._thread = threading.Thread(target=_run, name="aiops-eventbus", daemon=True)
        self._thread.start()
        self._thread_ready.wait(timeout=2.0)

    async def publish(self, event: Event) -> None:
        if self._loop is None:
            await self.start()
        queue = self._queue
        if queue is None:
            return
        await queue.put(event)

    def publish_nowait(self, event: Event) -> None:
        if self._loop is None:
            self.start_background()
        loop = self._loop
        queue = self._queue
        if loop is None or queue is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            queue.put_nowait(event)
            return
        if loop.is_running():
            loop.call_soon_threadsafe(queue.put_nowait, event)
            return
        queue.put_nowait(event)

    async def join(self) -> None:
        queue = self._queue
        if queue is None:
            return
        if self._loop is None:
            return
        if self._loop is asyncio.get_running_loop():
            await queue.join()
            return
        future = asyncio.run_coroutine_threadsafe(queue.join(), self._loop)
        await asyncio.wrap_future(future)

    async def stop(self) -> None:
        loop = self._loop
        task = self._task
        thread = self._thread

        self._loop = None
        self._task = None
        self._queue = None
        self._thread = None
        self._thread_ready.clear()

        if loop is None:
            return

        if task is not None:
            try:
                if loop is asyncio.get_running_loop():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                else:
                    loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass

        if thread is not None and thread.is_alive():
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=2.0)
        elif loop.is_running():
            try:
                loop.stop()
            except RuntimeError:
                pass

    async def _process_loop(self) -> None:
        queue = self._queue
        if queue is None:
            return
        while True:
            event = await queue.get()
            try:
                await self._dispatch_event(event)
            finally:
                queue.task_done()

    async def _dispatch_event(self, event: Event) -> None:
        handlers = list(self._listeners.get(type(event), []))
        if not handlers:
            return

        async def invoke(handler: EventHandler, item: Event) -> None:
            try:
                result = handler(item)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception(
                    "event_handler_failed",
                    extra={"event_type": type(item).__name__, "handler": getattr(handler, "__name__", str(handler))},
                )

        await asyncio.gather(*(invoke(h, event) for h in handlers), return_exceptions=True)


_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def new_event(source: str) -> Event:
    return Event(timestamp=time.time(), source=source)
