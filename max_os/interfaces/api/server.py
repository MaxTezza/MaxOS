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

from max_os.utils.config import load_settings

# ... (Previous imports)

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
            # Keep connection alive, listen for commands from GUI (optional)
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
    """
    Called by other parts of MaxOS to push updates.
    Types: 'transcript', 'twin_state', 'agent_status', 'reflex'
    """
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
    """Allows the GUI to send a text command to MaxOS."""
    if runner_ref:
        # We need to inject this into the runner's loop
        # For simplicity, we assume the runner exposes a queue or method
        # This is asynchronous fire-and-forget for the API response
        logger.info(f"API Command received: {cmd.text}")
        if hasattr(runner_ref, "inject_command"):
             await runner_ref.inject_command(cmd.text)
        return {"status": "queued", "command": cmd.text}
    return {"status": "error", "message": "Runner not linked"}
