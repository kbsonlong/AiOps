from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, Iterable, Protocol, TypeVar

S = TypeVar("S")


class Middleware(Protocol[S]):
    def __call__(
        self,
        state: S,
        call_next: Callable[[S], Awaitable[S]],
    ) -> S | Awaitable[S]: ...


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _ensure_async_handler(fn: Callable[[S], Any]) -> Callable[[S], Awaitable[S]]:
    async def _handler(state: S) -> S:
        return await _maybe_await(fn(state))

    return _handler


def _ensure_async_middleware(mw: Middleware[S]) -> Callable[[S, Callable[[S], Awaitable[S]]], Awaitable[S]]:
    async def _mw(state: S, call_next: Callable[[S], Awaitable[S]]) -> S:
        return await _maybe_await(mw(state, call_next))

    return _mw


@dataclass(frozen=True, slots=True)
class MiddlewareChain(Generic[S]):
    middlewares: tuple[Middleware[S], ...] = ()

    def add(self, middleware: Middleware[S]) -> MiddlewareChain[S]:
        return MiddlewareChain(self.middlewares + (middleware,))

    def extend(self, middlewares: Iterable[Middleware[S]]) -> MiddlewareChain[S]:
        return MiddlewareChain(self.middlewares + tuple(middlewares))

    def compose(self, other: MiddlewareChain[S]) -> MiddlewareChain[S]:
        return MiddlewareChain(self.middlewares + other.middlewares)

    def handler(self, terminal: Callable[[S], Any] | None = None) -> Callable[[S], Awaitable[S]]:
        if terminal is None:
            async def _terminal(state: S) -> S:
                return state
        else:
            _terminal = _ensure_async_handler(terminal)

        call_next = _terminal
        for mw in reversed(self.middlewares):
            mw_async = _ensure_async_middleware(mw)
            prev_next = call_next

            async def _wrapped(state: S, _mw=mw_async, _next=prev_next) -> S:
                return await _mw(state, _next)

            call_next = _wrapped
        return call_next

    async def arun(self, state: S, terminal: Callable[[S], Any] | None = None) -> S:
        return await self.handler(terminal)(state)

    def run(self, state: S, terminal: Callable[[S], Any] | None = None) -> S:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(state, terminal=terminal))
        raise RuntimeError("MiddlewareChain.run() cannot be called inside a running event loop; use arun() instead.")
