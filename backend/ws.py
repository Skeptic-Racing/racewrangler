"""
WebSocket broadcast hub.

All connected clients receive the same JSON messages so any UI tab stays
in sync without polling.  The backend calls `broadcast()` after any state
change; the frontend listens and updates its local state.

Message format:
  { "type": "finish_trigger", "data": { "is_finish_triggered": bool, "finish_triggered_at": str|null } }
  { "type": "run_update",     "data": { ...run dict... } }
  { "type": "staged_run_update", "data": { "event_id": str } }
  { "type": "ping" }
"""
import asyncio
import json
from typing import Any
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        self._clients = [c for c in self._clients if c is not ws]

    async def broadcast(self, msg_type: str, data: Any = None):
        if not self._clients:
            return
        payload = json.dumps({"type": msg_type, "data": data or {}})
        dead = []
        for ws in self._clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def broadcast(msg_type: str, data: Any = None):
    await manager.broadcast(msg_type, data)
