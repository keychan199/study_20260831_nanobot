import asyncio

from langchain_core.messages import HumanMessage

from mini_nanobot.graph import build_agent


async def main() -> None:
    agent = build_agent()
    result = await agent.ainvoke(
        # {"messages": [HumanMessage(content="计算 (3+50)*10，只给出最终数字")]}
        {"messages": [HumanMessage(content="现在北京时间多少")]}
    )
    print(result["messages"][-1].content)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())