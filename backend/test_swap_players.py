"""
Test swap_players tool with LangGraph agent
"""
import asyncio
from app.agents.langgraph_chat_agent import langgraph_chat_agent

async def test_swap_query():
    """Test agent recognizing swap intent"""
    query = "Can you start Josh Allen over Dak Prescott and update my lineup"

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
            print(f"\n✅ Response:\n{update['message']}")
        elif update["type"] == "error":
            print(f"\n❌ Error: {update['message']}")

if __name__ == "__main__":
    asyncio.run(test_swap_query())
