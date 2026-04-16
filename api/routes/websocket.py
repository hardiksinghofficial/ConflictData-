from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
from api.database import db
import json
import logging

log = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                log.error(f"Failed to send WS message: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

async def listen_to_pg_events():
    """Background task to listen to PostgreSQL NOTIFY and broadcast via WS."""
    # We must maintain this connection open indefinitely
    while True:
        try:
            async with db.pool.acquire() as conn:
                await conn.add_listener("new_conflict_event", lambda c, pid, channel, payload: asyncio.create_task(manager.broadcast(payload)))
                while True:
                    await asyncio.sleep(60) # Keep holding the connection for LISTEN
        except Exception as e:
            log.error(f"WS PG Listener error: {e}, retrying in 5s...")
            await asyncio.sleep(5)
            
# Start listener lazily
listener_task = None

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global listener_task
    if listener_task is None and db.pool:
        listener_task = asyncio.create_task(listen_to_pg_events())
        
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
