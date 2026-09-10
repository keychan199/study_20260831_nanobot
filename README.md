# mini-nanobot

从零复现 [nanobot](https://github.com/pkoukk/nanobot) 的学习项目：不抄实现，按「build-guide + 参考答案 + 验收标准」的路线，用 LangChain 1.x / LangGraph 1.x 重写一个精简版 AI Agent 框架。

- 目标是**看懂每一层为什么存在**，而不是堆功能——每个模块先读参考实现、补测试、再对照验收
- Python ≥ 3.11，uv 管理依赖，src layout

## 重建历程

按依赖顺序自底向上推进，每层先搭骨架、写测试、再接进主链路：

| 阶段 | 内容 | 状态 |
|------|------|------|
| 0. 工程脚手架 | uv + setuptools 68 + src layout + .env 隔离配置 | ✅ 完成 |
| 1. 配置层 | pydantic v2 校验（`.env` → `ProviderConfig` / `AppConfig`），占位符检查、路径规范化 | ✅ 完成 |
| 2. 消息总线 | `MessageBus`：两条 `asyncio.Queue` 解耦 Channel 与 AgentService | ✅ 完成 |
| 3. 工具 | `calculator`（AST 安全求值）、`get_current_time` | ✅ 完成 |
| 4. 渠道层 | `BaseChannel` / `ConsoleChannel`（rich 交互、/help /new /exit）/ `ChannelManager` | ✅ 完成 |
| 5. 会话管理 | `SessionManager` + `SessionMetadataStore` Protocol + JSON 原子写（temp→fsync→replace） | ✅ 完成 |
| 6. 图与服务 | `create_agent` + `AsyncSqliteSaver` checkpoint（sessions.db）、`AgentService` 会话级锁 | 🔶 接线中 |
| 7. 中间件 | 动态提示词、模型/工具重试、调用预算、内置摘要压缩；自写 `SummaryArchiveMiddleware`（哈希去重归档）、`EmptyResponseRecoveryMiddleware`（空回复跳回重试，上限 2 次） | ✅ 完成 |
| 8. 记忆系统 | `MemoryBackend` Protocol、`FileMemoryBackend`（模板初始化、namespace 隔离、路径穿越防护、并发追加、坏行容错、Dream 游标、快照/恢复）、`MemoryStore` 同步兼容层 | 🔶 重构中 |

## 架构总览

```
ConsoleChannel ──inbound──> MessageBus ──consume──> AgentService ──ainvoke──> LangGraph Agent
     ▲                                                                        │
     └──outbound── MessageBus <──publish── AgentService <── middleware ────────┘

持久化：workspace/sessions.db（LangGraph checkpoint）
        workspace/sessions/sessions.json（会话元数据，原子写）
        workspace/memory/{SOUL,USER,MEMORY}.md + history.jsonl + .dream_cursor
```

关键设计：

- **Protocol 解耦**：`SessionMetadataStore`、`MemoryBackend`、`MemoryReader`、`PendingEventSource` 均为结构化协议，本地文件实现可替换成 Redis/SQLite
- **中间件管线**（`build_agent_middleware`）：动态提示词 → 模型重试（自写 `classify_error` 判断 4xx/5xx 是否值得重试）→ 工具重试 → 调用预算 → 内置摘要压缩 → 摘要归档 → 空响应恢复
- **写防御**：所有落盘走原子写；`history.jsonl` 读取时跳过坏行、追加时自动从新行开始

## 当前测试状态

```
uv run pytest -q          # 17 passed, 8 failed
```

- ✅ `test_config` / `test_bus` / `test_channel_manager` / `test_basic_tools` / `test_middleware` 全绿
- ❌ `test_memory_store` ×7：`_directory_lock()` 签名重构到一半，调用点未同步
- ❌ `test_session_manager::test_metadata_is_valid_atomic_json`：元数据文件路径断言待修

## 剩余工作量

按优先级排列：

1. **修复记忆模块锁重构**：`_directory_lock` 新签名统一到所有调用点（7 个测试即可转绿）
2. **`AgentService` 接线**：`service.py::_process` 中 `graph` / `memory` 还是自由变量，需要改为 `self.agent` 并注入 `FileMemoryBackend`（或 `MemoryStore` 包装）
3. **补齐 `AppConfig` 字段**：`graph.py` 已引用 `context_window` / `consolidation_ratio` / `max_iterations`，但 `config.py` 尚未定义（`.env.example` 已预留）
4. **补齐工具**：中间件已引用 `read_text_file`，提示词已提到 `create_goal`，两者都未实现
5. **控制台命令**：`/goal` `/stop` `/compact` `/dream` `/status` 已写进 HELP_TEXT，循环里未处理
6. **Dream（长期记忆巩固）**：游标、快照、history 归档等底座已就绪，缺「读 history → LLM 提炼 → 回写三份 md」的巩固逻辑
7. **Goal 图**：`AgentState.goal_state` / `goal_creation_allowed` 已预留，缺外层目标循环与 `force_compact` / `PendingEventSource` 的实现
8. **进阶项（.env 已预留参数）**：流式输出、Telegram 等 Web 渠道、MCP 工具接入、子 Agent 并发

## 快速开始

```bash
uv sync                          # 安装依赖
cp .env.example .env             # 填入 OPENAI_API_KEY / OPENAI_API_BASE
uv run mini-nanobot              # 启动控制台
uv run pytest                    # 跑测试
uv run python scripts/smoke_agent.py   # 不走 Bus 的最小 Agent 冒烟
```
