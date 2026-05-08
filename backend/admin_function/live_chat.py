from fastapi import WebSocket
from typing import Dict, Set

class LiveChatManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect(self, session_id: str, role: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.sessions:
            self.sessions[session_id] = {"user": set(), "agent": set()}
        self.sessions[session_id][role].add(websocket)

    def disconnect(self, session_id: str, role: str, websocket: WebSocket):
        try:
            self.sessions[session_id][role].remove(websocket)
            if (
                not self.sessions[session_id]["user"]
                and not self.sessions[session_id]["agent"]
            ):
                del self.sessions[session_id]
        except KeyError:
            pass

    async def broadcast(self, session_id: str, message: dict):
        if session_id not in self.sessions:
            return

        dead = []
        for role, conns in self.sessions[session_id].items():
            for ws in list(conns):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((session_id, role, ws))

        for s_id, role, ws in dead:
            self.disconnect(s_id, role, ws)


manager = LiveChatManager()
