from typing import Dict, Any, List
from app.agents.config import SYSTEM_PROMPTS, AGENT_MODELS
from app.agents.llm_client import llm_client
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

        # Get player names
        my_player_names = [players_data.get(p, {}).get('full_name', p) for p in my_players]
        their_player_names = [players_data.get(p, {}).get('full_name', p) for p in their_players]

        # Use Claude for final analysis
        context = f"""
Analyze this fantasy football trade:

MY TEAM GIVES: {', '.join(my_player_names)}
MY TEAM RECEIVES: {', '.join(their_player_names)}

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
            analysis_text = llm_client.create_message(
                model=self.model,
                system=self.system_prompt,
                messages=[{"role": "user", "content": context}],
                max_tokens=1500
            )

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
