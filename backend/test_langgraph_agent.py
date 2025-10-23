"""
Test LangGraph Chat Agent Tool Selection
Tests various user queries to verify the LLM selects appropriate tools
"""
import asyncio
import json
from app.agents.langgraph_chat_agent import langgraph_chat_agent

async def test_agent(query: str):
    """Test agent with a specific query"""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")

    async for update in langgraph_chat_agent.chat_stream(
        user_message=query,
        league_id="1059972487498645504",
        roster_id=1,
        week=8
    ):
        if update["type"] == "status":
            print(f"🔄 Status: {update['message']}")
        elif update["type"] == "response":
            print(f"\n✅ Response: {update['message']}")
        elif update["type"] == "error":
            print(f"\n❌ Error: {update['message']}")

async def main():
    """Run multiple test queries"""

    test_queries = [
        # Should trigger search_web tool
        "Search for best waiver wire RBs this week",

        # Should trigger analyze_defense_vs_position and analyze_player_matchup
        "Which of my starters have the best matchups this week?",

        # Should trigger get_player_news
        "What's the latest news on Christian McCaffrey?",

        # Should trigger get_roster
        "Show me my current lineup",

        # Should trigger multiple tools
        "Who should I start at RB this week? Check injuries and matchups.",
    ]

    for query in test_queries:
        await test_agent(query)
        await asyncio.sleep(2)  # Rate limiting

if __name__ == "__main__":
    asyncio.run(main())
