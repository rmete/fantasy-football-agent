"""
Conversational agent for answering fantasy football questions
Uses tool calling to fetch relevant data based on the question
"""
from typing import Dict, Any, List, AsyncGenerator
from app.agents.config import SYSTEM_PROMPTS, AGENT_MODELS
from app.agents.llm_client import llm_client
import asyncio
from app.tools import (
    sleeper_client,
    web_search_tool,
    reddit_tool,
    projection_tool,
    injury_tool,
    matchup_analyzer
)
from app.tools.defense_matchup import defense_matchup_analyzer
from app.tools.nfl_schedule import nfl_schedule_tool
import logging
import re

logger = logging.getLogger(__name__)

class ChatAgent:
    """Conversational agent for fantasy football questions"""

    def __init__(self):
        self.model = AGENT_MODELS["sit_start"]  # Reuse sit/start model
        self.conversation_history: List[Dict[str, str]] = []

    async def chat(
        self,
        user_message: str,
        league_id: str,
        roster_id: int,
        week: int = 1
    ) -> str:
        """
        Process a user question and return a helpful response

        Args:
            user_message: The user's question
            league_id: The league ID for context
            roster_id: The roster ID for context
            week: Current week number

        Returns:
            AI-generated response to the question
        """

        logger.info(f"Processing chat message: {user_message}")

        try:
            # Get roster and player data for context
            roster_data = await sleeper_client.get_league_rosters(league_id)
            players_data = await sleeper_client.get_players()

            # Find the user's roster
            user_roster = None
            for roster in roster_data:
                if roster.get("roster_id") == roster_id:
                    user_roster = roster
                    break

            if not user_roster:
                return "I couldn't find your roster. Please make sure you're viewing the correct league."

            # Determine what tools to use based on the question
            tools_data = await self._gather_relevant_data(
                user_message,
                user_roster,
                players_data,
                week
            )

            # Build context for the LLM
            context = self._build_context(
                user_message,
                user_roster,
                players_data,
                tools_data,
                week
            )

            # Get response from LLM
            response = llm_client.create_message(
                model=self.model,
                system=self._get_system_prompt(),
                messages=[
                    *self.conversation_history,
                    {"role": "user", "content": context}
                ],
                max_tokens=1500,
                temperature=0.7
            )

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response})

            # Keep only last 10 messages to avoid context overflow
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            return response

        except Exception as e:
            logger.error(f"Chat agent error: {e}")
            return f"I apologize, but I encountered an error processing your question. Please try rephrasing or ask something else."

    async def chat_stream(
        self,
        user_message: str,
        league_id: str,
        roster_id: int,
        week: int = 1
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming version of chat that yields status updates

        Yields:
            Dictionary with type and message/data
        """

        logger.info(f"Processing streaming chat message: {user_message}")

        try:
            # Status: Fetching roster data
            yield {"type": "status", "message": "Fetching your roster data..."}
            await asyncio.sleep(0.1)  # Small delay for visual effect

            # Get roster and player data for context
            roster_data = await sleeper_client.get_league_rosters(league_id)
            players_data = await sleeper_client.get_players()

            # Find the user's roster
            user_roster = None
            for roster in roster_data:
                if roster.get("roster_id") == roster_id:
                    user_roster = roster
                    break

            if not user_roster:
                yield {"type": "error", "message": "I couldn't find your roster. Please make sure you're viewing the correct league."}
                return

            # Status: Analyzing question
            yield {"type": "status", "message": "Analyzing your question..."}
            await asyncio.sleep(0.1)

            # Determine what tools to use and send appropriate status messages
            question_lower = user_message.lower()

            needs_web_search = any(word in question_lower for word in ['search', 'find', 'look up', 'waiver', 'news', 'latest'])
            needs_matchup = any(word in question_lower for word in ['best matchup', 'best match', 'favorable matchup', 'matchup'])

            if needs_web_search:
                yield {"type": "status", "message": "Searching the web..."}

            if needs_matchup:
                yield {"type": "status", "message": "Analyzing defensive matchups..."}

            # Gather data with status updates
            tools_data = await self._gather_relevant_data(
                user_message,
                user_roster,
                players_data,
                week
            )

            # Status: Building response
            yield {"type": "status", "message": "Summarizing insights..."}
            await asyncio.sleep(0.1)

            # Build context for the LLM
            context = self._build_context(
                user_message,
                user_roster,
                players_data,
                tools_data,
                week
            )

            # Status: Cooking response
            yield {"type": "status", "message": "Cooking up your answer..."}
            await asyncio.sleep(0.1)

            # Get response from LLM
            response = llm_client.create_message(
                model=self.model,
                system=self._get_system_prompt(),
                messages=[
                    *self.conversation_history,
                    {"role": "user", "content": context}
                ],
                max_tokens=1500,
                temperature=0.7
            )

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response})

            # Keep only last 20 messages
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            # Send final response
            yield {"type": "response", "message": response}

        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            yield {"type": "error", "message": f"I apologize, but I encountered an error: {str(e)}"}

    async def _gather_relevant_data(
        self,
        question: str,
        roster: Dict[str, Any],
        players_data: Dict[str, Any],
        week: int
    ) -> Dict[str, Any]:
        """Gather data from relevant tools based on the question"""

        question_lower = question.lower()
        data = {}

        # Determine which tools to use
        needs_injury_check = any(word in question_lower for word in ['injury', 'injured', 'health', 'hurt', 'out'])
        needs_matchup = any(word in question_lower for word in ['matchup', 'opponent', 'against', 'vs', 'favorable'])
        needs_defense_analysis = any(word in question_lower for word in ['best matchup', 'best match', 'favorable matchup', 'defense against', 'defense vs'])
        needs_news = any(word in question_lower for word in ['news', 'latest', 'recent', 'update'])
        needs_sentiment = any(word in question_lower for word in ['community', 'reddit', 'opinion', 'people think'])
        needs_sit_start = any(word in question_lower for word in ['start', 'sit', 'bench', 'play', 'lineup', 'who should'])
        needs_web_search = any(word in question_lower for word in ['search', 'find', 'look up', 'what is', 'tell me about', 'information about'])

        # Extract player names from question
        player_names = self._extract_player_names(question, roster, players_data)

        # If it's a general "who should I start" question with no specific players mentioned,
        # analyze the starters for key positions
        if needs_sit_start and len(player_names) == 0:
            starters = roster.get('starters', [])
            # Get key offensive players from starters (skip K and DEF for now)
            for player_id in starters[:5]:  # Analyze top 5 starters
                player_info = players_data.get(player_id, {})
                full_name = player_info.get('full_name', '')
                pos = player_info.get('position', '')
                if full_name and pos not in ['K', 'DEF']:
                    player_names.append((full_name, player_id))

        # If asking for best matchups, analyze all starters' defensive matchups
        if needs_defense_analysis or (needs_sit_start and 'matchup' in question_lower):
            try:
                starters = roster.get('starters', [])
                matchup_analyses = []

                for player_id in starters[:5]:  # Analyze top 5 starters
                    player_info = players_data.get(player_id, {})
                    player_name = player_info.get('full_name', '')
                    position = player_info.get('position', '')
                    team = player_info.get('team', '')

                    if position in ['QB', 'RB', 'WR', 'TE'] and team:
                        # Get opponent
                        opponent = await nfl_schedule_tool.get_team_opponent(team, week)

                        if opponent:
                            opponent_full = nfl_schedule_tool.get_team_full_name(opponent)

                            # Analyze the matchup
                            matchup_data = await defense_matchup_analyzer.analyze_player_matchup(
                                player_name, team, position, opponent_full, week
                            )

                            matchup_analyses.append({
                                'player': player_name,
                                'position': position,
                                'opponent': opponent_full,
                                'matchup_data': matchup_data
                            })

                data['matchup_analyses'] = matchup_analyses
                logger.info(f"Analyzed {len(matchup_analyses)} player matchups")

            except Exception as e:
                logger.error(f"Error analyzing matchups: {e}")

        # If general web search is needed (not player-specific), perform it
        if needs_web_search and len(player_names) == 0:
            try:
                search_results = await web_search_tool.general_search(question, max_results=3)
                data['web_search'] = {
                    'query': question,
                    'results': search_results
                }
            except Exception as e:
                logger.error(f"Error performing web search: {e}")

        # Gather data for mentioned players (or top players if general question)
        for player_name, player_id in player_names[:5]:  # Analyze up to 5 players
            player_data = {}
            player_info = players_data.get(player_id, {})
            position = player_info.get('position', '')
            team = player_info.get('team', '')

            try:
                if needs_injury_check:
                    player_data['injury'] = await injury_tool.check_player_injury_status(
                        player_id, player_name
                    )

                if needs_matchup and position and team:
                    # Get opponent (simplified - in production, fetch from schedule)
                    opponent = "OPP"
                    player_data['matchup'] = await matchup_analyzer.analyze_player_matchup(
                        player_name, team, opponent, position, week
                    )

                if needs_news:
                    news = await web_search_tool.search_player_news(player_name)
                    player_data['news'] = news[:2]  # Top 2 articles

                if needs_sentiment:
                    player_data['sentiment'] = await reddit_tool.get_player_sentiment(player_name)

                if needs_sit_start:
                    player_data['projection'] = await projection_tool.get_player_projection(
                        player_name, position, week
                    )

                # Always get web search for players if news is needed
                if needs_web_search or needs_news:
                    search_results = await web_search_tool.general_search(
                        f"{player_name} NFL fantasy football week {week}",
                        max_results=2
                    )
                    player_data['web_search'] = search_results

                data[player_name] = player_data

            except Exception as e:
                logger.error(f"Error gathering data for {player_name}: {e}")
                continue

        return data

    def _extract_player_names(
        self,
        question: str,
        roster: Dict[str, Any],
        players_data: Dict[str, Any]
    ) -> List[tuple]:
        """Extract player names mentioned in the question"""

        mentioned_players = []
        all_player_ids = roster.get('players', [])

        # Check each player on the roster to see if they're mentioned
        for player_id in all_player_ids:
            player_info = players_data.get(player_id, {})
            full_name = player_info.get('full_name', '')
            first_name = player_info.get('first_name', '')
            last_name = player_info.get('last_name', '')

            # Check if player is mentioned (case insensitive)
            if full_name and full_name.lower() in question.lower():
                mentioned_players.append((full_name, player_id))
            elif last_name and len(last_name) > 3 and last_name.lower() in question.lower():
                mentioned_players.append((full_name or last_name, player_id))

        return mentioned_players

    def _build_context(
        self,
        question: str,
        roster: Dict[str, Any],
        players_data: Dict[str, Any],
        tools_data: Dict[str, Any],
        week: int
    ) -> str:
        """Build context string for the LLM"""

        # Get roster summary
        starters = roster.get('starters', [])
        all_players = roster.get('players', [])
        bench = [p for p in all_players if p not in starters]

        context_parts = [
            f"User Question: {question}",
            f"\nCurrent Week: {week}",
            f"\nUser's Roster Summary:",
            f"- Total Players: {len(all_players)}",
            f"- Starters: {len(starters)}",
            f"- Bench: {len(bench)}",
        ]

        # Add starters list with names
        context_parts.append("\nStarting Lineup:")
        for player_id in starters:
            player = players_data.get(player_id, {})
            name = player.get('full_name', player_id)
            pos = player.get('position', 'Unknown')
            team = player.get('team', 'FA')
            context_parts.append(f"- {name} ({pos}, {team})")

        # Add bench list with names
        context_parts.append("\nBench Players:")
        for player_id in bench:
            player = players_data.get(player_id, {})
            name = player.get('full_name', player_id)
            pos = player.get('position', 'Unknown')
            team = player.get('team', 'FA')
            context_parts.append(f"- {name} ({pos}, {team})")

        # Add roster breakdown by position
        positions = {}
        for player_id in all_players:
            player = players_data.get(player_id, {})
            pos = player.get('position', 'Unknown')
            positions[pos] = positions.get(pos, 0) + 1

        context_parts.append("\nRoster by Position:")
        for pos, count in sorted(positions.items()):
            context_parts.append(f"- {pos}: {count}")

        # Add matchup analyses first (if any)
        if 'matchup_analyses' in tools_data:
            matchup_data = tools_data['matchup_analyses']
            context_parts.append("\nDefensive Matchup Analysis:")

            for analysis in matchup_data:
                player = analysis.get('player', 'Unknown')
                position = analysis.get('position', 'N/A')
                opponent = analysis.get('opponent', 'Unknown')
                matchup_info = analysis.get('matchup_data', {})

                recommendation = matchup_info.get('overall_recommendation', 'neutral')
                summary = matchup_info.get('summary', 'No summary available')

                context_parts.append(f"\n{player} ({position}) vs {opponent}:")
                context_parts.append(f"  Matchup: {recommendation.upper()}")
                context_parts.append(f"  Analysis: {summary[:200]}...")

        # Add general web search results (if any)
        if 'web_search' in tools_data:
            web_data = tools_data['web_search']
            context_parts.append("\nWeb Search Results:")
            context_parts.append(f"Query: {web_data.get('query', 'N/A')}")
            for idx, result in enumerate(web_data.get('results', [])[:3], 1):
                context_parts.append(f"\n{idx}. {result.get('title', 'No title')}")
                context_parts.append(f"   {result.get('content', 'No content')[:200]}...")
                context_parts.append(f"   URL: {result.get('url', 'No URL')}")

        # Add tool-gathered data
        if tools_data:
            context_parts.append("\nRelevant Player Data:")
            for player_name, data in tools_data.items():
                if player_name == 'web_search':
                    continue  # Already handled above

                context_parts.append(f"\n{player_name}:")

                if 'injury' in data:
                    context_parts.append(f"  Injury Status: {data['injury']['injury_status']}")
                    context_parts.append(f"  Recommendation: {data['injury']['recommendation']}")

                if 'matchup' in data:
                    context_parts.append(f"  Matchup Rating: {data['matchup']['matchup_rating']}/10")
                    context_parts.append(f"  Matchup: {data['matchup']['recommendation']}")

                if 'projection' in data:
                    context_parts.append(f"  Projected Points: {data['projection']['projected_points']}")
                    context_parts.append(f"  Floor-Ceiling: {data['projection']['floor']}-{data['projection']['ceiling']}")

                if 'news' in data and data['news']:
                    context_parts.append(f"  Recent News: {data['news'][0]['title']}")

                if 'sentiment' in data:
                    context_parts.append(f"  Community Sentiment: {data['sentiment']['sentiment_score']} ({data['sentiment']['confidence']})")

                if 'web_search' in data and data['web_search']:
                    context_parts.append(f"  Latest Web Results:")
                    for idx, result in enumerate(data['web_search'][:2], 1):
                        context_parts.append(f"    {idx}. {result.get('title', 'No title')}")
                        context_parts.append(f"       {result.get('content', '')[:150]}...")

        return "\n".join(context_parts)

    def _get_system_prompt(self) -> str:
        """Get system prompt for the chat agent"""
        return """You are an expert fantasy football advisor assistant. Your role is to help users make informed decisions about their fantasy football lineup.

When answering questions:
1. Be conversational and friendly while remaining professional
2. Provide specific, actionable recommendations based on the data provided
3. Explain your reasoning clearly so users understand the logic
4. If you don't have enough data to answer confidently, say so
5. Consider multiple factors: injuries, matchups, recent performance, projections
6. When comparing players, give a clear recommendation with confidence level
7. Keep responses concise but informative (2-4 paragraphs typically)
8. Use the user's roster data to give personalized advice

Important: Base your answers ONLY on the data provided in the context. Don't make up player statistics or news."""


# Singleton instance
chat_agent = ChatAgent()
