"""
Test if agent asks clarifying questions for incomplete swap requests
"""
import asyncio
from app.agents.langgraph_chat_agent import langgraph_chat_agent

async def test_incomplete_swap():
    """Test agent handling incomplete lineup change request"""

    test_queries = [
        "Start Christian McCaffrey",
        "Bench my QB",
        "I want to start a different running back",
    ]

    for query in test_queries:
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
                print(f"\n✅ Response:\n{update['message']}\n")
            elif update["type"] == "error":
                print(f"\n❌ Error: {update['message']}\n")

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_incomplete_swap())
