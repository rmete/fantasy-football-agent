"""
LangChain Tool Schemas with Descriptions
Tools are grouped by specialist agent for efficient context management
"""
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from app.tools import (
    web_search_tool,
    sleeper_client,
    projection_tool,
    injury_tool,
    reddit_tool
)
from app.tools.defense_matchup import defense_matchup_analyzer
from app.tools.nfl_schedule import nfl_schedule_tool
from app.tools.browser.browser_tools import BROWSER_TOOLS


# ============================================================================
# RESEARCH AGENT TOOLS - Web search, news, defensive ratings, schedules
# ============================================================================

@tool
async def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web for fantasy football information, news, and analysis.

    Use this tool when the user asks to:
    - Search for information ("search for waiver wire pickups")
    - Find latest news ("what's the latest on CMC?")
    - Look up general fantasy football advice
    - Research player performance or trends

    Args:
        query: The search query (e.g., "best waiver wire RBs week 8 2025")
        max_results: Number of results to return (default 5)

    Returns:
        List of search results with title, url, content, and relevance score
    """
    return await web_search_tool.general_search(query, max_results)


@tool
async def get_player_news(player_name: str) -> List[Dict[str, Any]]:
    """
    Get the latest news articles about a specific NFL player.

    Use this tool when the user asks about:
    - Latest news on a player
    - Recent updates or developments
    - Player-specific information

    Args:
        player_name: Full name of the player (e.g., "Christian McCaffrey")

    Returns:
        List of recent news articles about the player
    """
    return await web_search_tool.search_player_news(player_name, max_results=3)


@tool
async def analyze_defense_vs_position(
    defense_team: str,
    position: str,
    week: int,
    year: int = 2025
) -> Dict[str, Any]:
    """
    Analyze how a defense performs against a specific position.

    Use this tool when the user asks about:
    - Defensive matchups ("How are the Falcons against RBs?")
    - Which players have good/bad matchups
    - Defense rankings vs positions

    Args:
        defense_team: Team name (e.g., "Falcons", "Patriots")
        position: Position code ("RB", "WR", "QB", "TE")
        week: NFL week number
        year: NFL season year (default 2025)

    Returns:
        Dictionary with matchup analysis, recommendation (favorable/neutral/unfavorable),
        and web search insights about the defense's performance
    """
    return await defense_matchup_analyzer.analyze_defense_vs_position(
        defense_team, position, week, year
    )


@tool
async def get_team_opponent(team_abbr: str, week: int) -> Optional[str]:
    """
    Find out which team an NFL team is playing in a specific week.

    Use this tool to:
    - Determine matchups for the week
    - Find out who a player's team is facing

    Args:
        team_abbr: Team abbreviation (e.g., "KC", "SF", "BAL")
        week: NFL week number

    Returns:
        Opponent team abbreviation or None if not found
    """
    return await nfl_schedule_tool.get_team_opponent(team_abbr, week)


# ============================================================================
# ROSTER MANAGER TOOLS - View and modify lineup
# ============================================================================

@tool
async def get_roster(league_id: str, roster_id: int) -> Dict[str, Any]:
    """
    Get the current roster including starters and bench players.

    Use this tool when the user wants to:
    - See their current lineup
    - View who's starting vs benched
    - Check their roster composition

    Args:
        league_id: Sleeper league ID
        roster_id: User's roster ID

    Returns:
        Dictionary with starters, bench players, and roster metadata
    """
    rosters = await sleeper_client.get_league_rosters(league_id)
    for roster in rosters:
        if roster.get("roster_id") == roster_id:
            return roster
    return {}


@tool
def identify_player_by_name(player_name: str, players_data: Dict[str, Any]) -> Optional[str]:
    """
    Find a player's ID by their name from the players database.

    Use this tool to convert player names to IDs for roster operations.

    Args:
        player_name: Player's full or partial name
        players_data: Dictionary of all NFL players

    Returns:
        Player ID if found, None otherwise
    """
    player_name_lower = player_name.lower()

    for player_id, player_info in players_data.items():
        full_name = player_info.get("full_name", "").lower()
        first_name = player_info.get("first_name", "").lower()
        last_name = player_info.get("last_name", "").lower()

        if (player_name_lower in full_name or
            player_name_lower == last_name or
            full_name.startswith(player_name_lower)):
            return player_id

    return None


@tool
async def swap_players(
    player_to_start: str,
    player_to_bench: str,
    reason: str = "User requested lineup change"
) -> Dict[str, Any]:
    """
    Propose swapping a bench player into the starting lineup.

    IMPORTANT: Use this tool IMMEDIATELY when the user explicitly asks to:
    - "Start [Player A] over [Player B]"
    - "Bench [Player A] and start [Player B]"
    - "Swap [Player A] with [Player B]"
    - "Can you start [Player A] over [Player B]"
    - "Update my lineup to start [Player A]"

    This tool creates a proposal for the lineup change. You should call this
    tool AFTER analyzing why the swap makes sense (e.g., after checking
    projections, matchups, or injuries).

    Args:
        player_to_start: Name of the player to move into starting lineup
        player_to_bench: Name of the player to move to bench
        reason: Brief explanation for the swap (e.g., "Better matchup" or "Higher projection")

    Returns:
        Dictionary with proposed change details and approval requirement
    """
    return {
        "success": True,
        "action": "swap_players",
        "player_to_start": player_to_start,
        "player_to_bench": player_to_bench,
        "reason": reason,
        "needs_approval": True,
        "message": (
            f"✅ Proposed lineup change:\n\n"
            f"  🔼 START: **{player_to_start}**\n"
            f"  🔽 BENCH: **{player_to_bench}**\n"
            f"  💡 Reason: {reason}\n\n"
            f"⚠️  **Action Required:**\n"
            f"This change requires your approval in the Sleeper app. "
            f"Sleeper uses OAuth authentication for roster modifications, "
            f"so you'll need to manually make this change in the app.\n\n"
            f"**Next Steps:**\n"
            f"1. Open your Sleeper app\n"
            f"2. Go to your team's roster\n"
            f"3. Move {player_to_start} to your starting lineup\n"
            f"4. Move {player_to_bench} to your bench"
        )
    }


# ============================================================================
# ANALYSIS AGENT TOOLS - Projections, injuries, sentiment
# ============================================================================

@tool
async def get_player_projection(
    player_name: str,
    position: str,
    week: int
) -> Dict[str, Any]:
    """
    Get fantasy point projections for a player.

    Use this tool when the user asks about:
    - How many points a player is projected to score
    - Floor/ceiling estimates
    - Expected performance

    Args:
        player_name: Player's full name
        position: Position ("QB", "RB", "WR", "TE")
        week: NFL week number

    Returns:
        Dictionary with projected_points, floor, ceiling, and confidence
    """
    return await projection_tool.get_player_projection(player_name, position, week)


@tool
async def check_injury_status(player_id: str, player_name: str) -> Dict[str, Any]:
    """
    Check a player's injury status and game availability.

    Use this tool when the user asks about:
    - Player injuries
    - If someone will play
    - Injury designations (Q, D, OUT, IR)

    Args:
        player_id: Sleeper player ID
        player_name: Player's full name

    Returns:
        Dictionary with injury_status, game_status, and recommendation
    """
    return await injury_tool.check_player_injury_status(player_id, player_name)


@tool
async def get_community_sentiment(player_name: str) -> Dict[str, Any]:
    """
    Analyze community sentiment about a player from r/fantasyfootball.

    Use this tool when the user asks about:
    - What people think about a player
    - Community opinions
    - Hype or concerns around a player

    Args:
        player_name: Player's full name

    Returns:
        Dictionary with sentiment_score, confidence, and sample opinions
    """
    return await reddit_tool.get_player_sentiment(player_name)


@tool
async def analyze_player_matchup(
    player_name: str,
    player_team: str,
    player_position: str,
    opponent_team: str,
    week: int
) -> Dict[str, Any]:
    """
    Complete matchup analysis for a specific player against their opponent.

    Use this tool when the user asks about:
    - How a specific player's matchup looks
    - If a player has a good week
    - Matchup-based start/sit decisions

    Args:
        player_name: Player's full name
        player_team: Player's team abbreviation
        player_position: Position code
        opponent_team: Opposing team name
        week: NFL week number

    Returns:
        Comprehensive matchup analysis with recommendation and supporting data
    """
    return await defense_matchup_analyzer.analyze_player_matchup(
        player_name, player_team, player_position, opponent_team, week
    )


# Tool lists for each specialist agent
RESEARCH_TOOLS = [
    search_web,
    get_player_news,
    analyze_defense_vs_position,
    get_team_opponent
]

ROSTER_TOOLS = [
    get_roster,
    identify_player_by_name,
    swap_players
]

ANALYSIS_TOOLS = [
    get_player_projection,
    check_injury_status,
    get_community_sentiment,
    analyze_player_matchup
]

# All tools combined (for supervisor if needed)
ALL_TOOLS = RESEARCH_TOOLS + ROSTER_TOOLS + ANALYSIS_TOOLS + BROWSER_TOOLS
