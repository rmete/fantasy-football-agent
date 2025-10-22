from typing import TypedDict, List, Dict, Any, Optional, Annotated
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
