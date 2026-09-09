from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage

from .bus import InboundMessage, MessageBus, OutboundMessage
# from .graph import build_agent
from .session import SessionManager

logger = logging.getLogger("mini_nanobot")


class AgentService:
    def __init__(self, bus: MessageBus, graph, session: SessionManager) -> None:
        self.bus = bus
        self.agent = graph
        self.sessions = session

    async def run(self) -> None:
        while True:
            msg = await self.bus.consume_inbound()
            try:
                # 让同一会话的请求串行执行，避免并发写同一 thread_id 的 checkpoint 时数据冲突
                async with self.sessions.lock_for(msg.session_id):
                    await self._process(msg)
                # await self._process(msg)
            except Exception as exc:
                logger.exception("处理失败")
                await self._reply(msg, f"处理失败：{exc}")

    async def _process(self, msg: InboundMessage) -> None:
        # result = await self.agent.ainvoke(
        #     {"messages": [HumanMessage(content=msg.content)]},
        #     config={"configurable": {"thread_id": msg.session_id}},
        # )
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=msg.content)]},
            config={"configurable": {"thread_id": msg.session_id}},
            context=AgentContext(session_id=msg.session_id, memory=memory, pending=None),
        )
        content = str(result["messages"][-1].content)
        await self._reply(msg, content)

    async def _reply(self, msg: InboundMessage, content: str) -> None:
        await self.bus.publish_outbound(
            OutboundMessage(
                channel=msg.channel,
                session_id=msg.session_id,
                content=content,
            )
        )