"""程序入口：把 Bus + Channel + AgentService 组装起来跑一个完整的 mini-nanobot。

流程：

    ConsoleChannel --inbound--> MessageBus --consume--> AgentService --graph--> LLM/工具
    ConsoleChannel <--outbound-- MessageBus <--publish-- AgentService

`ChannelManager` 负责启动 channel、把 outbound 消息路由回 channel；
`AgentService` 负责跑 LangGraph 图。两边只通过 `MessageBus` 打交道。
"""


from __future__ import annotations

import asyncio
import logging

from .bus import MessageBus
from .channels import ChannelManager, ConsoleChannel
from .config import ConfigurationError, load_config
from .service import AgentService
from .session import SessionManager
from .graph import create_app

logging.basicConfig(level=logging.WARNING)


async def _main() -> None:
    cfg = load_config()  # 提前校验 .env
    cfg.ensure_dirs()
    bus = MessageBus()
    session = SessionManager(cfg.workspace_dir)
    console = ConsoleChannel(bus, session)
    manager = ChannelManager(bus, [console])
    async with create_app(cfg) as graph:
        service = AgentService(bus, graph, session)
        service_task = asyncio.create_task(service.run())
        await manager.start()
        try:
            await manager.wait_until_all_stopped()
        finally:
            service_task.cancel()
            await manager.stop()
            await asyncio.gather(service_task, return_exceptions=True)


def run() -> None:
    try:
        asyncio.run(_main())
    except ConfigurationError as exc:
        print(f"启动失败：{exc}")
    except KeyboardInterrupt:
        pass