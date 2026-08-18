"""A minimal async pub/sub bus tying device telemetry to feature plugins and the GUI.

Deliberately tiny: this is not a message broker, just an in-process fan-out so
a feature like the telemetry logger doesn't need to know which devices exist,
and the GUI doesn't need to poll every device on its own timer if it doesn't
want to.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, payload: Any) -> None:
        for handler in list(self._subscribers.get(topic, ())):
            await handler(payload)
