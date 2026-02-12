"""WebSocket connection manager for streaming simulation frames."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per simulation ID.

    Thread-safe: frame callbacks come from simulation threads,
    but WebSocket sends must happen on the asyncio event loop.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, sim_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if sim_id not in self._connections:
            self._connections[sim_id] = []
        self._connections[sim_id].append(websocket)
        logger.info("WebSocket connected for simulation %s", sim_id)

    async def disconnect(self, sim_id: str, websocket: WebSocket) -> None:
        if sim_id in self._connections:
            self._connections[sim_id] = [
                ws for ws in self._connections[sim_id] if ws != websocket
            ]
            if not self._connections[sim_id]:
                del self._connections[sim_id]

    async def send_event(self, sim_id: str, event: dict[str, Any]) -> None:
        """Send an event to all WebSocket connections for a simulation."""
        if sim_id not in self._connections:
            return

        message = json.dumps(event)
        dead: list[WebSocket] = []

        for ws in self._connections.get(sim_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(sim_id, ws)

    def broadcast_from_thread(self, sim_id: str, event: dict[str, Any]) -> None:
        """Thread-safe broadcast — schedules send on the event loop."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self.send_event(sim_id, event), self._loop
        )
