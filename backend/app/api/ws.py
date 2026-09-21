"""WebSocket live streaming endpoint for real-time forensic updates.

Clients subscribe to /ws/live to receive reactive events (new_alert, detection_complete, etc.)
without manual polling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.events import ForensicEvent, event_bus

logger = logging.getLogger("chainsentinel.api.ws")
router = APIRouter(tags=["Live Feed"])


@router.websocket("/ws/live")
async def live_feed(websocket: WebSocket) -> None:
    """Live bidirectional forensic feed broadcasting detection, alert, and case events."""
    await websocket.accept()
    logger.info("WebSocket client connected to /ws/live from %s", websocket.client)

    queue = await event_bus.subscribe()
    try:
        # Send initial connection handshake event
        handshake = ForensicEvent(
            type="connected",
            data={"status": "online", "message": "ChainSentinel Live Stream Ready"},
        )
        await websocket.send_text(handshake.to_json())

        while True:
            # Wait for either incoming message from client or event from event_bus
            event = await queue.get()
            await websocket.send_text(event.to_json())
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally from /ws/live")
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        await event_bus.unsubscribe(queue)
