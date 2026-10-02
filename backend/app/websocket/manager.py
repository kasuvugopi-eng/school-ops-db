from fastapi import WebSocket
from collections import defaultdict
import json

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[tuple[str, WebSocket]]] = defaultdict(list)
    
    async def connect(self, websocket: WebSocket, school_id: str, user_id: str):
        await websocket.accept()
        self.connections[school_id].append((user_id, websocket))
    
    def disconnect(self, websocket: WebSocket, school_id: str):
        self.connections[school_id] = [
            (uid, ws) for uid, ws in self.connections[school_id] if ws != websocket
        ]
    
    async def broadcast_to_school(self, school_id: str, message: dict):
        for user_id, ws in list(self.connections.get(school_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws, school_id)
    
    async def send_to_user(self, school_id: str, user_id: str, message: dict):
        for uid, ws in list(self.connections.get(school_id, [])):
            if uid == user_id:
                try:
                    await ws.send_json(message)
                except Exception:
                    self.disconnect(ws, school_id)

ws_manager = ConnectionManager()
