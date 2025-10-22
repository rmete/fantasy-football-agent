from typing import Dict, Any
from app.agents.state import AgentState
from app.agents.sit_start_agent import sit_start_agent
from app.agents.trade_agent import trade_agent
from app.tools import sleeper_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """Main orchestrator that routes tasks to specialized agents"""

    def __init__(self):
        pass

    async def initialize_state(self, state: AgentState) -> AgentState:
        """Initialize state with required data"""

        logger.info(f"Initializing agent task: {state['task_type']}")

        # Fetch roster data
        rosters = await sleeper_client.get_league_rosters(state["league_id"])
        my_roster = next(
            (r for r in rosters if r["roster_id"] == state["roster_id"]),
            None
        )

        # Fetch players data
        players_data = await sleeper_client.get_players()

        state["roster_data"] = my_roster
        state["players_data"] = players_data
        state["started_at"] = datetime.utcnow()
        state["current_step"] = "initialized"

        return state

    async def route_task(self, state: AgentState) -> AgentState:
        """Route to appropriate agent based on task type"""

        task_type = state["task_type"]

        logger.info(f"Routing task: {task_type}")

        if task_type in ["sit_start", "lineup_optimization"]:
            state["current_step"] = "analyzing_players"
            results = await sit_start_agent.analyze_lineup_decision(state)
            state["analysis_results"]["sit_start"] = results
            state["recommendations"] = results["start_recommendations"]

        elif task_type == "trade_analysis":
            state["current_step"] = "analyzing_trade"

            # Get trade parameters from input
            input_data = state.get("input_data", {})
            my_players = input_data.get("my_players", [])
            their_players = input_data.get("their_players", [])

            # Get all rosters for context
            rosters = await sleeper_client.get_league_rosters(state["league_id"])

            results = await trade_agent.analyze_trade(
                my_players,
                their_players,
                state["roster_data"],
                {},  # Their roster would be fetched
                state["players_data"],
                state.get("league_data", {})
            )

            state["analysis_results"]["trade"] = results
            state["recommendations"] = [results]

        return state

    async def finalize_results(self, state: AgentState) -> AgentState:
        """Finalize and package results"""

        logger.info("Finalizing results")

        state["current_step"] = "completed"
        state["completed_at"] = datetime.utcnow()

        return state

    async def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent workflow"""

        try:
            # Initialize state with defaults
            state: AgentState = {
                "user_id": initial_state["user_id"],
                "league_id": initial_state["league_id"],
                "roster_id": initial_state["roster_id"],
                "task_type": initial_state["task_type"],
                "task_id": initial_state.get("task_id", ""),
                "messages": [],
                "roster_data": None,
                "players_data": None,
                "league_data": None,
                "matchup_data": None,
                "week": initial_state.get("week"),
                "analysis_results": {},
                "recommendations": [],
                "confidence_scores": {},
                "current_step": "pending",
                "next_action": None,
                "requires_approval": initial_state.get("requires_approval", False),
                "approved": None,
                "started_at": datetime.utcnow(),
                "completed_at": None,
                "error": None,
                "input_data": initial_state.get("input_data")
            }

            # Run workflow steps
            state = await self.initialize_state(state)
            state = await self.route_task(state)
            state = await self.finalize_results(state)

            return state

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {
                "error": str(e),
                "current_step": "failed"
            }

orchestrator = OrchestratorAgent()
