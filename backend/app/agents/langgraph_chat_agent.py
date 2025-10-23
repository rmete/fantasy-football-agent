"""
LangGraph-based Fantasy Football Chat Agent
Uses proper agent architecture with tool calling and state management
"""
from typing import AsyncGenerator, Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agents.state import ChatAgentState
from app.agents.llm_client import llm_client
from app.agents.tools_schema import ALL_TOOLS
from app.tools import sleeper_client
from app.utils.nfl_week import get_current_nfl_week
import logging

logger = logging.getLogger(__name__)


class LangGraphChatAgent:
    """
    Fantasy Football Chat Agent using LangGraph for intelligent tool selection
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph agent workflow"""

        # Create graph
        workflow = StateGraph(ChatAgentState)

        # Add nodes
        workflow.add_node("fetch_context", self._fetch_context_node)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(ALL_TOOLS))

        # Set entry point
        workflow.set_entry_point("fetch_context")

        # Add edges
        workflow.add_edge("fetch_context", "agent")

        # Conditional edge: agent decides whether to use tools or end
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )

        # After tools, go back to agent
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    async def _fetch_context_node(self, state: ChatAgentState) -> Dict[str, Any]:
        """Fetch roster and player data before agent processing"""

        logger.info("Fetching context data...")

        try:
            # Fetch roster data
            roster_data = await sleeper_client.get_league_rosters(state["league_id"])
            players_data = await sleeper_client.get_players()

            # Find user's roster
            user_roster = None
            if roster_data:
                for roster in roster_data:
                    if roster.get("roster_id") == state["roster_id"]:
                        user_roster = roster
                        break

            return {
                "roster_data": user_roster or {},
                "players_data": players_data or {},
                "status_message": "Context loaded"
            }
        except Exception as e:
            logger.error(f"Error fetching context: {e}")
            return {
                "roster_data": {},
                "players_data": {},
                "status_message": "Error loading context"
            }

    async def _agent_node(self, state: ChatAgentState) -> Dict[str, Any]:
        """Main agent decision-making node"""

        logger.info("Agent thinking...")

        # Get roster context
        roster = state.get("roster_data", {})
        players = state.get("players_data", {})

        # Build system message with context
        system_message = self._build_system_message(state, roster, players)

        # Prepare messages for LLM
        messages = [SystemMessage(content=system_message)] + state["messages"]

        # Get LLM to decide on tool usage
        # Bind tools to the model so it can decide which to call
        from langchain_anthropic import ChatAnthropic
        from app.core.config import settings

        model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.7
        ).bind_tools(ALL_TOOLS)

        response = await model.ainvoke(messages)

        return {
            "messages": [response],
            "status_message": "Agent responded"
        }

    def _should_continue(self, state: ChatAgentState) -> str:
        """Decide whether to continue to tools or end"""

        last_message = state["messages"][-1]

        # If the last message has tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(f"Agent requested tools: {[tc['name'] for tc in last_message.tool_calls]}")
            return "continue"

        # Otherwise, we're done
        return "end"

    def _build_system_message(
        self,
        state: ChatAgentState,
        roster: Dict[str, Any],
        players: Dict[str, Any]
    ) -> str:
        """Build context-rich system message"""

        week = state["week"]

        # Get roster summary
        starters = roster.get("starters", [])
        all_players = roster.get("players", [])
        bench = [p for p in all_players if p not in starters]

        # Build player lists
        starter_names = []
        for player_id in starters[:10]:  # Top 10 starters
            player = players.get(player_id, {})
            name = player.get("full_name", player_id)
            pos = player.get("position", "")
            team = player.get("team", "")
            starter_names.append(f"{name} ({pos}, {team})")

        bench_names = []
        for player_id in bench[:10]:  # Top 10 bench
            player = players.get(player_id, {})
            name = player.get("full_name", player_id)
            pos = player.get("position", "")
            team = player.get("team", "")
            bench_names.append(f"{name} ({pos}, {team})")

        system_prompt = f"""You are an expert fantasy football advisor assistant for Week {week} of the 2025 NFL season.

You have access to powerful tools to help answer questions:
- **search_web**: Search for any fantasy football information, waiver wire picks, news
- **get_player_news**: Get latest news on specific players
- **analyze_defense_vs_position**: Analyze how defenses perform vs positions (for matchup advice)
- **get_team_opponent**: Find out who teams are playing
- **get_roster**: View the user's current lineup
- **get_player_projection**: Get fantasy point projections
- **check_injury_status**: Check player injuries
- **get_community_sentiment**: See what r/fantasyfootball thinks
- **analyze_player_matchup**: Full matchup analysis for a player
- **swap_players**: Propose lineup changes (requires user approval)

USER'S ROSTER CONTEXT:
Starting Lineup ({len(starters)} players):
{chr(10).join(f"  • {name}" for name in starter_names)}

Bench ({len(bench)} players):
{chr(10).join(f"  • {name}" for name in bench_names)}

INSTRUCTIONS:
1. **Use tools intelligently**: When the user asks about waiver wire, news, matchups, or specific players, USE THE APPROPRIATE TOOLS
2. **Be specific**: Always mention player names, positions, and teams
3. **Provide reasoning**: Explain WHY you recommend something
4. **Use multiple tools**: Combine tools for comprehensive analysis (e.g., search_web + analyze_defense_vs_position)
5. **Be concise**: 2-4 paragraphs typically, unless asked for more detail

LINEUP CHANGE WORKFLOW (CRITICAL):
When the user asks to start a player (e.g., "Start Christian McCaffrey" or "Start CMC"), follow this EXACT process:

1. **Identify the player's position** from the roster context above
2. **Find all STARTING players at that same position** (e.g., if CMC is RB, find all starting RBs)
3. **Get projections** for the player they want to start AND all current starters at that position
4. **Compare projections** and identify the lowest-projected starter
5. **Suggest the optimal swap** to the user with reasoning:

   Example response format:
   "I found that you currently have [Player A] and [Player B] starting at RB. Here are their projections:
   • [Player A]: X points
   • [Player B]: Y points
   • Christian McCaffrey: Z points

   I recommend benching [lowest projected player] to start CMC because [reason].

   Should I propose this swap?"

6. **Wait for user confirmation** before calling swap_players tool
7. **Only call swap_players AFTER user confirms** they want the swap

CRITICAL: Do NOT immediately call swap_players. Always:
- Analyze the situation first
- Show the user their options
- Explain your recommendation
- Ask for confirmation
- Then call swap_players with the reason

EXAMPLES:
- "Search for waiver wire pickups" → Use search_web tool
- "Who should I start?" → Use analyze_player_matchup for multiple players
- "Latest on CMC?" → Use get_player_news
- "Best matchup?" → Use analyze_defense_vs_position for starters
- "Start Christian McCaffrey" → Get projections for CMC and current starting RBs, suggest who to bench, ask for confirmation

Answer the user's question using the tools available. Be helpful, specific, and data-driven."""

        return system_prompt

    async def chat_stream(
        self,
        user_message: str,
        league_id: str,
        roster_id: int,
        week: int,
        conversation_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat responses with agent status updates

        Yields status updates and final response
        """

        logger.info(f"LangGraph chat: {user_message}")

        # Build message history from conversation
        messages = []
        if conversation_history:
            for msg in conversation_history:
                # Handle both dict and Pydantic model
                role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
                content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")

                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # Add current message
        messages.append(HumanMessage(content=user_message))

        # Initialize state
        initial_state: ChatAgentState = {
            "messages": messages,
            "user_id": "default",  # TODO: Get from auth
            "league_id": league_id,
            "roster_id": roster_id,
            "week": week,
            "next_agent": None,
            "current_agent": "chat",
            "roster_data": None,
            "players_data": None,
            "tool_outputs": {},
            "status_message": None,
            "final_response": None,
            "needs_approval": False,
            "pending_action": None
        }

        try:
            # Stream status updates
            yield {"type": "status", "message": "Fetching your roster data..."}

            # Run the graph
            final_state = None
            async for event in self.graph.astream(initial_state):
                # Extract status from event
                if isinstance(event, dict):
                    for node_name, node_state in event.items():
                        if "status_message" in node_state and node_state["status_message"]:
                            yield {"type": "status", "message": node_state["status_message"]}

                        # Check if tools were called
                        if "messages" in node_state and len(node_state["messages"]) > 0:
                            last_msg = node_state["messages"][-1]
                            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                tool_names = [tc["name"] for tc in last_msg.tool_calls]
                                yield {"type": "status", "message": f"Using tools: {', '.join(tool_names)}..."}

                        final_state = node_state

            # Get final response
            if final_state and "messages" in final_state:
                last_message = final_state["messages"][-1]

                if hasattr(last_message, "content"):
                    response_text = last_message.content
                else:
                    response_text = str(last_message)

                yield {"type": "response", "message": response_text}
            else:
                yield {"type": "response", "message": "I apologize, but I couldn't generate a response."}

        except Exception as e:
            logger.error(f"LangGraph chat error: {e}", exc_info=True)
            yield {"type": "error", "message": f"Error: {str(e)}"}


# Singleton instance
langgraph_chat_agent = LangGraphChatAgent()
