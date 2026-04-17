import json
import logging
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


class WebSocketManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        # user_id → list of connected WebSockets
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
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self._connections[user_id].remove(ws)

    async def broadcast_to_all(self, message: dict):
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, message)

    def _count(self):
        return sum(len(v) for v in self._connections.values())


# Global singleton — imported by trading_engine
ws_manager = WebSocketManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = Query(...)):
    """
    ws://host/ws/{user_id}?token=<jwt>
    Streams: trade_update | metrics_update | log_event
    """
    # Authenticate via JWT in query param
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        token_user_id = payload.get("sub")
        if token_user_id != user_id:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive — client can also send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
