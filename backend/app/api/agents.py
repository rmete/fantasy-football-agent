from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.agents.orchestrator import orchestrator
import logging
import uuid

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

@router.post("/sit-start")
async def run_sit_start_analysis(request: SitStartRequest):
    """Run sit/start analysis for a roster"""

    try:
        task_id = str(uuid.uuid4())

        logger.info(f"Starting sit/start analysis for league {request.league_id}")

        # Run orchestrator
        initial_state = {
            "user_id": request.user_id,
            "league_id": request.league_id,
            "roster_id": request.roster_id,
            "task_type": "sit_start",
            "task_id": task_id,
            "week": request.week or 1
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

@router.get("/health")
async def agents_health():
    """Check if agents are configured correctly"""

    from app.core.config import settings

    health = {
        "status": "healthy",
        "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
        "sleeper_configured": bool(settings.SLEEPER_USERNAME)
    }

    if not settings.ANTHROPIC_API_KEY:
        health["status"] = "degraded"
        health["message"] = "ANTHROPIC_API_KEY not configured"

    return health
