from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from shared.logging_client import LoggerClient


class WebSocketManager:
    def __init__(self, logger: LoggerClient):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.logger = logger

    async def connect(self, websocket: WebSocket, stream_id: str):
        """Connect a new WebSocket client"""
        await websocket.accept()

        if stream_id not in self.active_connections:
            self.active_connections[stream_id] = set()

        self.active_connections[stream_id].add(websocket)
        await self.logger.info(
            "New WebSocket connection", metadata={"stream_id": stream_id}
        )

    def disconnect(self, websocket: WebSocket, stream_id: str):
        """Disconnect a WebSocket client"""
        if stream_id in self.active_connections:
            self.active_connections[stream_id].discard(websocket)

    async def broadcast_to_clients(self, stream_id: str, message: dict):
        """Broadcast a message to all connected clients for a stream"""
        if stream_id not in self.active_connections:
            return

        disconnected_clients = set()
        for websocket in self.active_connections[stream_id]:
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected_clients.add(websocket)
            except Exception as e:
                await self.logger.error(f"Error broadcasting message: {str(e)}")
                disconnected_clients.add(websocket)

        # Remove disconnected clients
        for websocket in disconnected_clients:
            self.disconnect(websocket, stream_id)

    async def close_all(self):
        """Close all WebSocket connections"""
        for stream_id, connections in self.active_connections.items():
            for websocket in connections:
                try:
                    await websocket.close()
                except Exception:
                    pass
        self.active_connections.clear()
