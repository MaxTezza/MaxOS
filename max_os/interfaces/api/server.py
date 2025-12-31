"""
The Neural Link.
FastAPI Backend for MaxOS V2.
Serves the Frontend and providing a WebSocket stream for real-time state.
"""

import asyncio
from typing import List, Dict, Any
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from max_os.utils.config import load_settings

logger = structlog.get_logger("max_os.api")

app = FastAPI(title="MaxOS Neural Link")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
runner_ref = None

def set_runner(runner):
    global runner_ref
    runner_ref = runner

# Load global settings manager
settings_manager = load_settings()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial state
        await websocket.send_json({
            "type": "settings_update",
            "payload": settings_manager.accessibility
        })
        
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket Error", error=str(e))
        manager.disconnect(websocket)

class SettingsUpdate(BaseModel):
    category: str
    key: str
    value: Any

@app.post("/settings/update")
async def update_setting(update: SettingsUpdate):
    """Updates a setting and saves to disk."""
    full_key = f"{update.category}.{update.key}"
    try:
        settings_manager.update(full_key, update.value)
        # Broadcast the change to all clients
        await broadcast_state_update("settings_update", settings_manager.accessibility)
        return {"status": "success", "new_value": update.value}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Broadcast Helper ---
async def broadcast_state_update(state_type: str, data: Any):
    await manager.broadcast({
        "type": state_type,
        "payload": data,
        "timestamp": asyncio.get_event_loop().time()
    })

# --- Models ---
class CommandRequest(BaseModel):
    text: str

@app.post("/command")
async def send_command(cmd: CommandRequest):
    if runner_ref:
        logger.info(f"API Command received: {cmd.text}")
        if hasattr(runner_ref, "inject_command"):
             await runner_ref.inject_command(cmd.text)
        return {"status": "queued", "command": cmd.text}
    return {"status": "error", "message": "Runner not linked"}
