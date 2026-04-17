"""
WebSocket manager — streams live trading events to connected frontends.
The singleton `manager` (formerly `ws_manager`) is imported by trading_engine.
"""
import logging
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


class WebSocketManager:
    """Manages all active WebSocket connections, keyed by user_id."""

    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        logger.info(f"WS connected: user={user_id} (total={self._count()})")

    def disconnect(self, websocket: WebSocket, user_id: str):
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        logger.info(f"WS disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        """Send a JSON message to all connections for a user."""
        dead = []
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.get(user_id, []).remove(ws)

    async def broadcast_to_all(self, message: dict):
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, message)

    def _count(self):
        return sum(len(v) for v in self._connections.values())


# ── Global singleton ─────────────────────────────────────────
# Named `manager` so trading_engine can do: from routes.websocket import manager
manager = WebSocketManager()

# Backwards-compat alias (in case anything still references ws_manager)
ws_manager = manager


@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = Query(...)):
    """
    ws://host/api/ws/{user_id}?token=<jwt>
    Streams: trade_update | metrics_update | log_event
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        token_user_id = payload.get("sub")
        if token_user_id != user_id:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
