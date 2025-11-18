"""MaxOS REST API"""
from fastapi import FastAPI
from pydantic import BaseModel

from max_os.core.orchestrator import AIOperatingSystem

app = FastAPI()
orchestrator = AIOperatingSystem()


class IntentRequest(BaseModel):
    text: str


@app.post("/intent")
def handle_intent(request: IntentRequest):
    """
    Handles a user's intent.
    """
    response = orchestrator.handle_text(request.text)
    return response
