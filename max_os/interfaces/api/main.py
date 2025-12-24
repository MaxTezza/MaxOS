"""MaxOS REST API"""

from fastapi import FastAPI
from pydantic import BaseModel

from max_os.core.orchestrator import AIOperatingSystem

app = FastAPI()
orchestrator = AIOperatingSystem()


class IntentRequest(BaseModel):
    text: str


class MultiAgentRequest(BaseModel):
    """Request for multi-agent processing."""

    query: str
    context: dict = {}
    show_work: bool = True


@app.post("/intent")
async def handle_intent(request: IntentRequest):
    """
    Handles a user's intent.
    """
    response = await orchestrator.handle_text(request.text)
    return response


@app.post("/multi-agent")
async def multi_agent_query(request: MultiAgentRequest):
    """
    Process query with multi-agent debate system.
    
    Example:
    POST /multi-agent
    {
        "query": "Should I buy a house or keep renting?",
        "context": {"budget": 50000, "location": "Seattle"},
        "show_work": true
    }
    
    Returns:
        final_answer: Final synthesized answer
        confidence: Confidence score (0.0-1.0)
        agents_used: List of agents that contributed
        work_logs: Detailed work from each agent (if show_work=True)
        debate_log: Debate transcript (if debate occurred and show_work=True)
    """
    if not orchestrator.multi_agent:
        return {
            "error": "Multi-agent system not enabled",
            "message": "Enable multi_agent in settings.yaml to use this feature",
        }

    result = await orchestrator.multi_agent.process_with_debate(
        user_query=request.query, context=request.context, show_work=request.show_work
    )

    return {
        "final_answer": result.final_answer,
        "confidence": result.confidence,
        "agents_used": result.agents_used,
        "work_logs": result.agent_work_logs if request.show_work else None,
        "debate_log": result.debate_log if request.show_work else None,
        "manager_review": {
            "needs_debate": result.manager_review.needs_debate,
            "conflicts": result.manager_review.conflicts,
            "confidence": result.manager_review.confidence,
        }
        if request.show_work
        else None,
    }

