# """让 Agent 的系统提示词"动态生成"而不是写死"""
# from langchain.agents.middleware import dynamic_prompt, ModelRequest
# import inspect

# @dynamic_prompt # 动态提示词中间件 返回值作为 system prompt
# async def runtime_prompt(request: ModelRequest) -> str:
#     context: AgentContext = request.runtime.context
#     memory_files = context.memory.read_all_memory_files()
#     if inspect.isawaitable(memory_files): #同时支持同步和异步的`MemoryReader` 实现
#         memory_files = await memory_files
#     return build_system_prompt(
#         memory_files,
#         request.state.get("goal_state"),
#     )


"""LangChain `create_agent` 的中间件组装。

标准能力（模型/工具重试、调用预算、摘要）直接使用 LangChain
内置 middleware。本章只保留两件项目特有的事：

1. 每次模型调用前动态注入本地长期记忆与 Goal；
2. 把 `SummarizationMiddleware` 产生的摘要归档给 Dream。
"""

from __future__ import annotations

import hashlib
import inspect
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,          # 基础中间件
    ModelCallLimitMiddleware, # 模型调用预算中间件
    ModelRequest,             # 模型请求中间件
    ModelRetryMiddleware,     # 模型重试中间件
    SummarizationMiddleware,  # 摘要中间件
    ToolCallLimitMiddleware,  # 工具调用预算中间件
    ToolRetryMiddleware,      # 工具重试中间件
    dynamic_prompt,           # 动态提示词中间件
    hook_config,              # 钩子配置中间件
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from .prompts import build_system_prompt
from .retry import classify_error
from .state import AgentContext, AgentState


def _content_is_blank(content: Any) -> bool:
    if isinstance(content, str):
        return not content.strip()
    if isinstance(content, list):
        return not any(
            isinstance(block, dict)
            and block.get("type") in {"text", "output_text"}
            and str(block.get("text", "")).strip()
            for block in content
        )
    return content is None


class SummaryArchiveMiddleware(AgentMiddleware[AgentState, AgentContext]):
    """把 LangChain 摘要消息追加到 Dream 的 history.jsonl，内容哈希用于去重。"""

    state_schema = AgentState

    async def abefore_model(
        self,
        state: AgentState,
        runtime,
    ) -> dict[str, Any] | None:
        summaries = [
            message
            for message in state["messages"]
            if isinstance(message, HumanMessage)
            and message.additional_kwargs.get("lc_source") == "summarization"
        ]
        if not summaries:
            return None

        content = str(summaries[-1].content)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if state.get("last_archived_summary_hash") == digest:
            return None

        result = runtime.context.memory.append_history(content, kind="summary")
        if inspect.isawaitable(result):
            await result
        return {"last_archived_summary_hash": digest}


class EmptyResponseRecoveryMiddleware(AgentMiddleware[AgentState, AgentContext]):
    """空响应最多重试两次，避免终端只显示一个空行。"""

    state_schema = AgentState

    async def abefore_agent(
        self,
        state: AgentState,
        runtime,
    ) -> dict[str, Any]:
        return {"empty_response_count": 0}

    @hook_config(can_jump_to=["model"])
    async def aafter_model(
        self,
        state: AgentState,
        runtime,
    ) -> dict[str, Any] | None:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage):
            return None
        if last.tool_calls or not _content_is_blank(last.content):
            return {"empty_response_count": 0}

        retries = state.get("empty_response_count", 0)
        if retries >= 2:
            return None
        return {"empty_response_count": retries + 1, "jump_to": "model"}


def _should_retry_model(exc: Exception) -> bool:
    return classify_error(exc, attempt=0).should_retry


def build_agent_middleware(
    llm: BaseChatModel,
    *,
    context_window: int,
    consolidation_ratio: float,
    max_model_calls: int,
) -> list[AgentMiddleware]:
    """构造主 Agent middleware，顺序决定模型调用前后的处理先后。"""

    trigger_tokens = max(1000, int(context_window * consolidation_ratio))
    keep_tokens = max(500, int(context_window * 0.2))

    @dynamic_prompt
    async def runtime_prompt(request: ModelRequest) -> str:
        context: AgentContext = request.runtime.context
        memory_files = context.memory.read_all_memory_files()
        if inspect.isawaitable(memory_files):
            memory_files = await memory_files
        return build_system_prompt(
            memory_files,
            request.state.get("goal_state"),
        )

    middleware: list[AgentMiddleware] = [
        runtime_prompt,           # 动态提示词中间件
        ModelRetryMiddleware(
            max_retries=2,
            retry_on=_should_retry_model,
            on_failure="error",
        ),                       # 模型重试中间件
        ToolRetryMiddleware(
            max_retries=1,
            tools=["calculator", "get_current_time", "read_text_file"],
            on_failure="continue",
        ),                       # 工具重试中间件
        ModelCallLimitMiddleware(
            run_limit=max_model_calls,
            exit_behavior="end",
        ),                       # 模型调用预算中间件
        ToolCallLimitMiddleware(
            run_limit=max_model_calls * 2,
            exit_behavior="continue",
        ),                       # 工具调用预算中间件
        SummarizationMiddleware(
            llm,
            trigger=("tokens", trigger_tokens),
            keep=("tokens", keep_tokens),
        ),                       # 摘要中间件
        SummaryArchiveMiddleware(), # 摘要归档中间件
        EmptyResponseRecoveryMiddleware(), # 空响应恢复中间件
    ]
    return middleware