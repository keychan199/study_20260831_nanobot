from __future__ import annotations

import asyncio

from ..bus import MessageBus
from .base import BaseChannel


class ChannelManager:
    """通道管理器，负责启动和停止所有通道"""

    def __init__(self, bus: MessageBus, channels: list[BaseChannel]) -> None:
        self.bus = bus
        self.channels = {c.name: c for c in channels}
        self._tasks: list[asyncio.Task[None]] = []
        # 两套任务的区别在于分发员的位置：
        # 1. 通道任务：负责启动和停止每个通道
        # 2. 分发员任务：负责从总线消费出站消息并分发给对应的通道
        # 3. 通道任务在分发员任务之前执行，确保所有通道都已启动
        # 4. 分发员任务在通道任务之后结束(杀掉)，确保所有通道都已停止
        self._channel_tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        for channel in self.channels.values():
            task = asyncio.create_task(
                channel.start(),
                name=f"channel:{channel.name}",
            )
            self._channel_tasks.append(task)
            self._tasks.append(task)
        self._tasks.append(asyncio.create_task(self._dispatch_outbound()))

    async def stop(self) -> None:
        for channel in self.channels.values():
            await channel.stop()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True) #把控制权交回事件循环

    async def _dispatch_outbound(self) -> None:
        while True:
            msg = await self.bus.consume_outbound()
            channel = self.channels.get(msg.channel)
            if channel is None:
                continue
            if msg.event == "delta":
                await channel.send_delta(msg.session_id, msg.content, msg.metadata)
            elif msg.event == "stream_end":
                await channel.send_delta_end(msg.session_id, msg.metadata)
            else:
                await channel.send(msg.session_id, msg.content, msg.metadata)

    async def wait_until_all_stopped(self) -> None:
        if self._channel_tasks:
            await asyncio.gather(*self._channel_tasks)