"""
Test smart swap suggestions with the enhanced agent
Tests that agent suggests who to bench based on projections
"""
import asyncio
from app.agents.langgraph_chat_agent import langgraph_chat_agent

async def test_smart_swap():
    """Test agent making intelligent bench suggestions"""

    # Query: User wants to start a player but doesn't say who to bench
    query = "I want to start Christian McCaffrey at running back"

    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    print("Testing: Agent should:")
    print("1. Get projections for CMC and current starting RBs")
    print("2. Compare projections")
    print("3. Suggest who to bench (lowest projection)")
    print("4. Ask user for confirmation")
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
            print(f"\n✅ Agent Response:\n{update['message']}\n")
        elif update["type"] == "error":
            print(f"\n❌ Error: {update['message']}\n")

if __name__ == "__main__":
    asyncio.run(test_smart_swap())
