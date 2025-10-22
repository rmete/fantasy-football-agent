# Phase 5: LangGraph Agents

**Goal**: Implement multi-agent AI orchestration using LangGraph and Claude

**Estimated Time**: 10-12 hours

**Dependencies**: Phases 1-4

## Overview

This is the core AI brain of the application. We'll build:
- Agent state management with LangGraph
- Individual specialized agents (Sit/Start, Trade, Waiver, etc.)
- Main orchestrator agent that coordinates sub-agents
- Tool integration for all agents
- Human-in-the-loop approval workflows

## Architecture

```
User Request
     ↓
Orchestrator Agent
     ↓
┌────┴────┬────────┬──────────┬──────────┐
│         │        │          │          │
Sit/Start Trade  Waiver   Lineup   Monitor
Agent    Agent   Agent    Agent    Agent
     ↓
  [Uses Tools]
     ↓
  Decision
```

## Tasks Breakdown

### Task 5.1: Agent State & Base Configuration

#### backend/app/agents/state.py

```python
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import add_messages
from datetime import datetime

class AgentState(TypedDict):
    """Shared state across all agents"""

    # User context
    user_id: str
    league_id: str
    roster_id: int

    # Current task
    task_type: str  # sit_start, trade_analysis, waiver_wire, etc.
    task_id: str

    # Messages (conversation history)
    messages: Annotated[List[Dict[str, Any]], add_messages]

    # Data cache
    roster_data: Optional[Dict[str, Any]]
    players_data: Optional[Dict[str, Any]]
    league_data: Optional[Dict[str, Any]]
    matchup_data: Optional[Dict[str, Any]]

    # Agent outputs
    analysis_results: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]

    # Workflow control
    current_step: str
    next_action: Optional[str]
    requires_approval: bool
    approved: Optional[bool]

    # Metadata
    started_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]
```

#### backend/app/agents/config.py

```python
from anthropic import Anthropic
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Claude client
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Model configurations
AGENT_MODELS = {
    "orchestrator": "claude-3-5-sonnet-20241022",
    "sit_start": "claude-3-5-sonnet-20241022",
    "trade": "claude-3-5-sonnet-20241022",
    "waiver": "claude-3-5-sonnet-20241022",
    "lineup": "claude-3-5-sonnet-20241022",
}

# Agent prompts
SYSTEM_PROMPTS = {
    "orchestrator": """You are an AI orchestrator for a fantasy football management system.
Your role is to understand user requests and route them to specialized agents.

Available agents:
- sit_start_agent: Analyzes players and makes sit/start recommendations
- trade_agent: Evaluates trades and suggests counter-offers
- waiver_agent: Monitors waiver wire and suggests pickups
- lineup_agent: Optimizes weekly lineup based on matchups

Determine which agent(s) to invoke based on the user's request.""",

    "sit_start": """You are a fantasy football sit/start expert.
Analyze players using multiple data sources:
- Player statistics and trends
- Opponent matchup strength
- Recent news and injury reports
- Expert projections
- Community sentiment

Provide clear recommendations with confidence scores (0-100) and reasoning.""",

    "trade": """You are a fantasy football trade analyzer.
Evaluate trades by considering:
- Player values and rankings
- Team needs and roster construction
- Bye week coverage
- League scoring settings
- ROS (rest of season) outlook

Suggest fair trades and explain the reasoning.""",

    "waiver": """You are a fantasy football waiver wire expert.
Identify valuable pickups by analyzing:
- Recent performance trends
- Upcoming matchups
- Injury situation on depth charts
- Volume and opportunity metrics
- Breakout potential

Prioritize recommendations and suggest drop candidates.""",

    "lineup": """You are a fantasy football lineup optimizer.
Build optimal lineups considering:
- Projected points and floor/ceiling
- Matchup difficulty
- Home/away splits
- Weather conditions
- Injury status and practice reports

Maximize expected points while managing risk.""",
}
```

### Task 5.2: Sit/Start Decision Agent

#### backend/app/agents/sit_start_agent.py

```python
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.config import anthropic_client, SYSTEM_PROMPTS, AGENT_MODELS
from app.tools import (
    sleeper_client,
    web_search_tool,
    reddit_tool,
    projection_tool,
    injury_tool,
    matchup_analyzer
)
import logging

logger = logging.getLogger(__name__)

class SitStartAgent:
    """Agent for making sit/start decisions"""

    def __init__(self):
        self.model = AGENT_MODELS["sit_start"]
        self.system_prompt = SYSTEM_PROMPTS["sit_start"]

    async def analyze_player(
        self,
        player_id: str,
        player_name: str,
        position: str,
        opponent: str,
        week: int,
        players_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Comprehensive player analysis"""

        logger.info(f"Analyzing {player_name} for week {week}")

        # Gather data from multiple sources in parallel
        player_info = players_data.get(player_id, {})

        # 1. Check injury status
        injury_status = await injury_tool.check_player_injury_status(
            player_id, player_name
        )

        # 2. Get matchup analysis
        matchup = await matchup_analyzer.analyze_player_matchup(
            player_name,
            player_info.get("team", ""),
            opponent,
            position,
            week
        )

        # 3. Get projections
        projection = await projection_tool.get_player_projection(
            player_name, position, week
        )

        # 4. Search recent news
        news = await web_search_tool.search_player_news(
            player_name,
            additional_context=f"week {week} fantasy outlook"
        )

        # 5. Get community sentiment
        sentiment = await reddit_tool.get_player_sentiment(player_name)

        # Compile all data
        analysis_data = {
            "player_id": player_id,
            "player_name": player_name,
            "position": position,
            "team": player_info.get("team"),
            "opponent": opponent,
            "week": week,
            "injury_status": injury_status,
            "matchup": matchup,
            "projection": projection,
            "recent_news": news[:3],
            "sentiment": sentiment
        }

        # Use Claude to synthesize analysis
        decision = await self._make_decision(analysis_data)

        return decision

    async def _make_decision(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use Claude to make final sit/start decision"""

        # Prepare context for Claude
        context = f"""
Analyze this fantasy football player for sit/start decision:

Player: {analysis_data['player_name']} ({analysis_data['position']})
Team: {analysis_data['team']} vs {analysis_data['opponent']}
Week: {analysis_data['week']}

Injury Status: {analysis_data['injury_status']['injury_status']}
Injury Recommendation: {analysis_data['injury_status']['recommendation']}

Matchup Rating: {analysis_data['matchup']['matchup_rating']}/10
Matchup Recommendation: {analysis_data['matchup']['recommendation']}

Projection: {analysis_data['projection']['projected_points']} points
Floor/Ceiling: {analysis_data['projection']['floor']} - {analysis_data['projection']['ceiling']}

Reddit Sentiment: {analysis_data['sentiment']['sentiment_score']} ({analysis_data['sentiment']['confidence']})
Positive/Negative: {analysis_data['sentiment']['positive_mentions']}/{analysis_data['sentiment']['negative_mentions']}

Recent News:
{chr(10).join([f"- {n['title']}" for n in analysis_data['recent_news']])}

Based on all this data, provide:
1. START or SIT recommendation
2. Confidence score (0-100)
3. Brief reasoning (2-3 sentences)
4. Key factors influencing decision
"""

        try:
            response = anthropic_client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": context}
                ]
            )

            recommendation_text = response.content[0].text

            # Parse response (in production, use structured output)
            decision = self._parse_recommendation(
                recommendation_text,
                analysis_data
            )

            return decision

        except Exception as e:
            logger.error(f"Error making decision: {e}")
            return {
                "player": analysis_data['player_name'],
                "recommendation": "SIT",
                "confidence": 50,
                "reasoning": "Error occurred during analysis",
                "error": str(e)
            }

    def _parse_recommendation(
        self,
        text: str,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Claude's response into structured format"""

        # Simple parsing (in production, use structured output)
        recommendation = "START" if "START" in text.upper() else "SIT"

        # Extract confidence (look for numbers)
        confidence = 75  # Default
        for line in text.split('\n'):
            if 'confidence' in line.lower():
                # Try to extract number
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    confidence = int(numbers[0])
                    break

        return {
            "player_id": analysis_data['player_id'],
            "player_name": analysis_data['player_name'],
            "position": analysis_data['position'],
            "week": analysis_data['week'],
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": text,
            "supporting_data": {
                "projection": analysis_data['projection']['projected_points'],
                "matchup_rating": analysis_data['matchup']['matchup_rating'],
                "injury_status": analysis_data['injury_status']['injury_status'],
                "sentiment_score": analysis_data['sentiment']['sentiment_score']
            }
        }

    async def analyze_lineup_decision(
        self,
        state: AgentState
    ) -> Dict[str, Any]:
        """Analyze multiple players for lineup decisions"""

        roster_data = state["roster_data"]
        players_data = state["players_data"]
        week = state.get("week", 1)

        starters = roster_data.get("starters", [])
        bench = roster_data.get("players", [])

        # Remove starters from bench list
        bench = [p for p in bench if p not in starters]

        # Analyze all players
        all_analyses = []

        for player_id in starters + bench[:5]:  # Limit to avoid rate limits
            player_info = players_data.get(player_id, {})
            if not player_info:
                continue

            analysis = await self.analyze_player(
                player_id,
                player_info.get("full_name", "Unknown"),
                player_info.get("position", ""),
                player_info.get("opponent", ""),
                week,
                players_data
            )
            all_analyses.append(analysis)

        # Sort by confidence and recommendation
        start_recommendations = [
            a for a in all_analyses if a["recommendation"] == "START"
        ]
        sit_recommendations = [
            a for a in all_analyses if a["recommendation"] == "SIT"
        ]

        return {
            "total_analyzed": len(all_analyses),
            "start_recommendations": sorted(
                start_recommendations,
                key=lambda x: x["confidence"],
                reverse=True
            ),
            "sit_recommendations": sorted(
                sit_recommendations,
                key=lambda x: x["confidence"],
                reverse=True
            ),
            "all_analyses": all_analyses
        }

sit_start_agent = SitStartAgent()
```

### Task 5.3: Trade Analyzer Agent

#### backend/app/agents/trade_agent.py

```python
from typing import Dict, Any, List
from app.agents.config import anthropic_client, SYSTEM_PROMPTS, AGENT_MODELS
from app.tools import sleeper_client, projection_tool
import logging

logger = logging.getLogger(__name__)

class TradeAgent:
    """Agent for analyzing trades"""

    def __init__(self):
        self.model = AGENT_MODELS["trade"]
        self.system_prompt = SYSTEM_PROMPTS["trade"]

    async def analyze_trade(
        self,
        my_players: List[str],
        their_players: List[str],
        my_roster: Dict[str, Any],
        their_roster: Dict[str, Any],
        players_data: Dict[str, Any],
        league_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a proposed trade"""

        logger.info(f"Analyzing trade: {my_players} for {their_players}")

        # Calculate player values
        my_value = await self._calculate_roster_value(my_players, players_data)
        their_value = await self._calculate_roster_value(their_players, players_data)

        # Analyze roster fit
        my_roster_impact = self._analyze_roster_impact(
            my_players, their_players, my_roster, players_data
        )
        their_roster_impact = self._analyze_roster_impact(
            their_players, my_players, their_roster, players_data
        )

        # Use Claude for final analysis
        context = f"""
Analyze this fantasy football trade:

MY TEAM GIVES: {', '.join([players_data.get(p, {}).get('full_name', p) for p in my_players])}
MY TEAM RECEIVES: {', '.join([players_data.get(p, {}).get('full_name', p) for p in their_players])}

Value Assessment:
- My players value: {my_value}
- Their players value: {their_value}
- Value difference: {their_value - my_value}

Roster Impact:
- My roster needs: {my_roster_impact['needs']}
- Positions I'm giving: {my_roster_impact['giving_positions']}
- Positions I'm receiving: {their_roster_impact['giving_positions']}

Should I accept this trade? Provide:
1. ACCEPT or REJECT recommendation
2. Confidence score (0-100)
3. Detailed reasoning
4. Potential counter-offer if rejecting
"""

        try:
            response = anthropic_client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=self.system_prompt,
                messages=[{"role": "user", "content": context}]
            )

            analysis_text = response.content[0].text

            return {
                "recommendation": "ACCEPT" if "ACCEPT" in analysis_text.upper() else "REJECT",
                "my_value": my_value,
                "their_value": their_value,
                "value_difference": their_value - my_value,
                "analysis": analysis_text,
                "my_roster_impact": my_roster_impact,
                "their_roster_impact": their_roster_impact
            }

        except Exception as e:
            logger.error(f"Trade analysis error: {e}")
            return {
                "recommendation": "REJECT",
                "error": str(e)
            }

    async def _calculate_roster_value(
        self,
        player_ids: List[str],
        players_data: Dict[str, Any]
    ) -> float:
        """Calculate total value of players"""

        total_value = 0.0

        for player_id in player_ids:
            player = players_data.get(player_id, {})
            # Use search_rank as proxy for value (lower is better)
            rank = player.get("search_rank", 999)
            # Convert to value score
            value = max(0, 100 - (rank / 10))
            total_value += value

        return round(total_value, 2)

    def _analyze_roster_impact(
        self,
        giving: List[str],
        receiving: List[str],
        roster: Dict[str, Any],
        players_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze impact on roster construction"""

        giving_positions = [
            players_data.get(p, {}).get("position", "")
            for p in giving
        ]
        receiving_positions = [
            players_data.get(p, {}).get("position", "")
            for p in receiving
        ]

        # Analyze roster needs (simplified)
        return {
            "giving_positions": giving_positions,
            "receiving_positions": receiving_positions,
            "needs": ["Depth needed"]  # Simplified
        }

    async def suggest_trade_targets(
        self,
        my_roster: Dict[str, Any],
        league_rosters: List[Dict[str, Any]],
        players_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest potential trade targets based on roster needs"""

        # Simplified implementation
        # In production: analyze roster gaps, find teams with surpluses

        suggestions = []

        # This would use more sophisticated analysis
        return suggestions

trade_agent = TradeAgent()
```

### Task 5.4: Orchestrator Agent

#### backend/app/agents/orchestrator.py

```python
from typing import Dict, Any
from langgraph.graph import StateGraph, END
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
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("initialize", self.initialize_state)
        workflow.add_node("route_task", self.route_task)
        workflow.add_node("sit_start", self.run_sit_start)
        workflow.add_node("trade_analysis", self.run_trade_analysis)
        workflow.add_node("finalize", self.finalize_results)

        # Add edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "route_task")

        # Conditional routing
        workflow.add_conditional_edges(
            "route_task",
            self.determine_next_agent,
            {
                "sit_start": "sit_start",
                "trade_analysis": "trade_analysis",
                "end": "finalize"
            }
        )

        workflow.add_edge("sit_start", "finalize")
        workflow.add_edge("trade_analysis", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

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

    def determine_next_agent(self, state: AgentState) -> str:
        """Route to appropriate agent based on task type"""

        task_type = state["task_type"]

        routing = {
            "sit_start": "sit_start",
            "lineup_optimization": "sit_start",
            "trade_analysis": "trade_analysis",
        }

        return routing.get(task_type, "end")

    async def run_sit_start(self, state: AgentState) -> AgentState:
        """Run sit/start analysis"""

        logger.info("Running sit/start agent")

        state["current_step"] = "analyzing_players"

        results = await sit_start_agent.analyze_lineup_decision(state)

        state["analysis_results"]["sit_start"] = results
        state["recommendations"] = results["start_recommendations"]

        return state

    async def run_trade_analysis(self, state: AgentState) -> AgentState:
        """Run trade analysis"""

        logger.info("Running trade agent")

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
            state = AgentState(
                user_id=initial_state["user_id"],
                league_id=initial_state["league_id"],
                roster_id=initial_state["roster_id"],
                task_type=initial_state["task_type"],
                task_id=initial_state.get("task_id", ""),
                messages=[],
                roster_data=None,
                players_data=None,
                league_data=None,
                matchup_data=None,
                analysis_results={},
                recommendations=[],
                confidence_scores={},
                current_step="pending",
                next_action=None,
                requires_approval=initial_state.get("requires_approval", False),
                approved=None,
                started_at=datetime.utcnow(),
                completed_at=None,
                error=None
            )

            # Add any additional input data
            if "input_data" in initial_state:
                state["input_data"] = initial_state["input_data"]

            # Run the graph
            final_state = await self.graph.ainvoke(state)

            return final_state

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {
                "error": str(e),
                "current_step": "failed"
            }

orchestrator = OrchestratorAgent()
```

## Testing

#### backend/tests/test_agents.py

```python
import asyncio
from app.agents.orchestrator import orchestrator

async def test_sit_start_agent():
    """Test sit/start agent workflow"""

    print("🤖 Testing Sit/Start Agent\n")

    initial_state = {
        "user_id": "test_user",
        "league_id": "YOUR_LEAGUE_ID",  # Replace with real league ID
        "roster_id": 1,
        "task_type": "sit_start",
        "task_id": "test_123"
    }

    result = await orchestrator.run(initial_state)

    print(f"Status: {result['current_step']}")
    print(f"Recommendations: {len(result.get('recommendations', []))}")

    for rec in result.get('recommendations', [])[:3]:
        print(f"\n{rec['player_name']} ({rec['position']})")
        print(f"  Recommendation: {rec['recommendation']}")
        print(f"  Confidence: {rec['confidence']}%")
        print(f"  Reasoning: {rec['reasoning'][:100]}...")

    print("\n✅ Sit/Start agent test complete!")

if __name__ == "__main__":
    asyncio.run(test_sit_start_agent())
```

## Success Criteria

After Phase 5:

1. ✅ LangGraph orchestrator can route tasks
2. ✅ Sit/Start agent analyzes players using multiple tools
3. ✅ Trade agent evaluates trade proposals
4. ✅ Claude API integration working
5. ✅ Agent state managed correctly
6. ✅ Error handling in place

## Next Steps

Proceed to **[Phase 6: Frontend Foundation](./phase-6-frontend.md)** to build the UI.

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [LangChain Documentation](https://python.langchain.com/)
