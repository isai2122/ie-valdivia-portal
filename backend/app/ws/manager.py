"""Gestor de conexiones WebSocket en memoria."""
import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket

log = logging.getLogger("ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._conns.add(ws)
        log.info("ws connected (total=%d)", len(self._conns))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._conns.discard(ws)
        log.info("ws disconnected (total=%d)", len(self._conns))

    async def broadcast(self, payload: Dict) -> None:
        async with self._lock:
            conns = list(self._conns)
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception as exc:  # noqa: BLE001
                log.warning("broadcast failed, dropping: %s", exc)
                await self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self._conns)


manager = ConnectionManager()
