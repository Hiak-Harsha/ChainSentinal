"""In-process asynchronous pub/sub event bus for ChainSentinel.

Allows backend modules (alerts, detection runs, correlation, cases) to publish
forensic events, and WebSocket endpoints to broadcast them to active clients.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import json
import logging
import time
from typing import Any

logger = logging.getLogger("chainsentinel.events")


@dataclass
class ForensicEvent:
    """Standardized event envelope for real-time streaming."""
    type: str  # 'new_alert' | 'detection_complete' | 'correlation_updated' | 'case_updated' | 'feedback_received'
    data: dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp <= 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventBus:
    """Broadcaster managing active subscriber asyncio queues."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[ForensicEvent]] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def subscribe(self) -> asyncio.Queue[ForensicEvent]:
        """Register a new listener queue."""
        self._loop = asyncio.get_running_loop()
        q: asyncio.Queue[ForensicEvent] = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(q)
            logger.info("New subscriber connected. Total subscribers: %d", len(self._subscribers))
        return q

    async def unsubscribe(self, q: asyncio.Queue[ForensicEvent]) -> None:
        """Unregister a listener queue."""
        async with self._lock:
            self._subscribers.discard(q)
            logger.info("Subscriber disconnected. Total subscribers: %d", len(self._subscribers))

    async def publish(self, event: ForensicEvent) -> None:
        """Broadcast an event to all connected queues."""
        async with self._lock:
            subscribers = list(self._subscribers)

        for q in subscribers:
            try:
                # If queue is full, drop oldest to prevent memory leakage
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(event)
            except Exception as e:
                logger.warning("Failed to deliver event to subscriber: %s", e)

    def publish_sync(self, event: ForensicEvent) -> None:
        """Synchronous helper to broadcast from non-async threads/routes."""
        target_loop = None
        try:
            target_loop = asyncio.get_running_loop()
        except RuntimeError:
            target_loop = self._loop

        if target_loop and target_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.publish(event), target_loop)
        else:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(event)
                except Exception:
                    pass



# Global application event bus
event_bus = EventBus()
