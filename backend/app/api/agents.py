from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
from app.agents.orchestrator import orchestrator
from app.agents.chat_agent import chat_agent
from app.agents.langgraph_chat_agent import langgraph_chat_agent
from app.utils.nfl_week import get_current_nfl_week, validate_week
import logging
import uuid
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])

class SitStartRequest(BaseModel):
    league_id: str
    roster_id: int
    week: Optional[int] = None
    user_id: str = "default_user"  # In production, get from auth

class TradeAnalysisRequest(BaseModel):
    league_id: str
    my_players: List[str]
    their_players: List[str]
    user_id: str = "default_user"

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    league_id: str
    roster_id: int
    week: Optional[int] = 1
    conversation_history: Optional[List[ChatMessage]] = []  # Previous messages for context
    # Model preferences
    model: Optional[str] = None  # Override default model
    temperature: Optional[float] = None  # Override default temperature

@router.post("/sit-start")
async def run_sit_start_analysis(request: SitStartRequest):
    """Run sit/start analysis for a roster"""

    try:
        task_id = str(uuid.uuid4())
        current_week = validate_week(request.week)

        logger.info(f"Starting sit/start analysis for league {request.league_id}, week {current_week}")

        # Run orchestrator
        initial_state = {
            "user_id": request.user_id,
            "league_id": request.league_id,
            "roster_id": request.roster_id,
            "task_type": "sit_start",
            "task_id": task_id,
            "week": current_week
        }

        result = await orchestrator.run(initial_state)

        return {
            "task_id": task_id,
            "status": "completed",
            "recommendations": result.get("recommendations", []),
            "total_analyzed": result.get("analysis_results", {}).get("sit_start", {}).get("total_analyzed", 0)
        }

    except Exception as e:
        logger.error(f"Sit/start analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trade-analysis")
async def run_trade_analysis(request: TradeAnalysisRequest):
    """Analyze a trade proposal"""

    try:
        task_id = str(uuid.uuid4())

        logger.info(f"Starting trade analysis for league {request.league_id}")

        # Run orchestrator
        initial_state = {
            "user_id": request.user_id,
            "league_id": request.league_id,
            "roster_id": 1,  # Would come from user's roster
            "task_type": "trade_analysis",
            "task_id": task_id,
            "input_data": {
                "my_players": request.my_players,
                "their_players": request.their_players
            }
        }

        result = await orchestrator.run(initial_state)

        trade_result = result.get("analysis_results", {}).get("trade", {})

        return {
            "task_id": task_id,
            "status": "completed",
            "recommendation": trade_result.get("recommendation"),
            "analysis": trade_result.get("analysis"),
            "my_value": trade_result.get("my_value"),
            "their_value": trade_result.get("their_value")
        }

    except Exception as e:
        logger.error(f"Trade analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """Chat with the AI agent about lineup decisions"""

    try:
        current_week = validate_week(request.week)
        logger.info(f"Chat request: {request.message[:50]}... (Week {current_week})")

        response = await chat_agent.chat(
            user_message=request.message,
            league_id=request.league_id,
            roster_id=request.roster_id,
            week=current_week
        )

        return {
            "response": response,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_with_agent_stream(request: ChatRequest):
    """Streaming chat with LangGraph agent and tool calling"""

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            current_week = validate_week(request.week)

            # Get response from LangGraph chat agent with streaming
            async for update in langgraph_chat_agent.chat_stream(
                user_message=request.message,
                league_id=request.league_id,
                roster_id=request.roster_id,
                week=current_week,
                conversation_history=request.conversation_history or []
            ):
                yield f"data: {json.dumps(update)}\n\n"

            # Send completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/week")
async def get_current_week():
    """Get current NFL week information"""
    from app.utils.nfl_week import get_nfl_week_info

    return get_nfl_week_info()

@router.get("/health")
async def agents_health():
    """Check if agents are configured correctly"""

    from app.core.config import settings

    health = {
        "status": "healthy",
        "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
        "sleeper_configured": bool(settings.SLEEPER_USERNAME),
        "current_week": get_current_nfl_week()
    }

    if not settings.ANTHROPIC_API_KEY:
        health["status"] = "degraded"
        health["message"] = "ANTHROPIC_API_KEY not configured"

    return health
