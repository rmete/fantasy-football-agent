"""
LangGraph State Schema for Fantasy Football Agents
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
from datetime import datetime
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ChatAgentState(TypedDict):
    """State for the conversational chat agent with tool calling"""

    # Conversation messages (LangChain format)
    messages: Annotated[List[BaseMessage], add_messages]

    # User context
    user_id: str
    league_id: str
    roster_id: int
    week: int

    # Agent coordination
    next_agent: Optional[str]  # Which specialist to route to
    current_agent: str  # Current agent name

    # Cached data
    roster_data: Optional[Dict[str, Any]]
    players_data: Optional[Dict[str, Any]]

    # Tool outputs (accumulated across agents)
    tool_outputs: Dict[str, Any]

    # Status updates for streaming UI
    status_message: Optional[str]

    # Final response
    final_response: Optional[str]

    # Human-in-the-loop for roster changes
    needs_approval: bool
    pending_action: Optional[Dict[str, Any]]


class AgentState(TypedDict):
    """Legacy state - keeping for backward compatibility with orchestrator"""

    # User context
    user_id: str
    league_id: str
    roster_id: int

    # Current task
    task_type: str  # sit_start, trade_analysis, waiver_wire, etc.
    task_id: str

    # Messages (conversation history)
    messages: List[Dict[str, Any]]

    # Data cache
    roster_data: Optional[Dict[str, Any]]
    players_data: Optional[Dict[str, Any]]
    league_data: Optional[Dict[str, Any]]
    matchup_data: Optional[Dict[str, Any]]

    # Week context
    week: Optional[int]

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

    # Input data for specific tasks
    input_data: Optional[Dict[str, Any]]
