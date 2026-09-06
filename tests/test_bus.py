import asyncio

from mini_nanobot.bus import InboundMessage, OutboundMessage, MessageBus


def test_roundtrip() -> None:
    async def scenario() -> None:
        bus = MessageBus()
        inbound = InboundMessage("console", "s1", "你好")
        await bus.publish_inbound(inbound)# 发布一条消息到 inbound 队列，inbound表示用户那边来的消息
        got = await bus.consume_inbound()# 从 inbound 队列消费一条消息
        assert got.content == "你好"

        await bus.publish_outbound(OutboundMessage(
            "console", "s1", "收到", event = "final"))# outbound表示agent那边来的消息
        out = await bus.consume_outbound()
        assert out.content == "收到"

    asyncio.run(scenario())
