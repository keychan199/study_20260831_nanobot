from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from mini_nanobot.middleware import (
    EmptyResponseRecoveryMiddleware,
    SummaryArchiveMiddleware,
)
from mini_nanobot.state import AgentContext


class _FakeMemory:
    def __init__(self) -> None:
        self.history: list[dict] = []

    def read_all_memory_files(self) -> dict[str, str]:
        return {"SOUL.md": "", "USER.md": "", "MEMORY.md": ""}

    def append_history(self, summary: str, *, kind: str = "summary") -> dict:
        entry = {"kind": kind, "content": summary}
        self.history.append(entry)
        return entry


def _runtime(memory: _FakeMemory | None = None) -> Runtime:
    return Runtime(
        context=AgentContext(session_id="thread", memory=memory or _FakeMemory())
    )


@pytest.mark.asyncio
async def test_empty_response_jumps_then_gives_up() -> None:
    mw = EmptyResponseRecoveryMiddleware()
    runtime = _runtime()
    blank = AIMessage(content="   ")

    await mw.abefore_agent({"messages": []}, runtime)

    first = await mw.aafter_model(
        {"messages": [blank], "empty_response_count": 0}, runtime
    )
    assert first is not None
    assert first["jump_to"] == "model"
    assert first["empty_response_count"] == 1

    second = await mw.aafter_model(
        {"messages": [blank], "empty_response_count": 1}, runtime
    )
    assert second is not None
    assert second["jump_to"] == "model"

    third = await mw.aafter_model(
        {"messages": [blank], "empty_response_count": 2}, runtime
    )
    assert third is None


@pytest.mark.asyncio
async def test_non_blank_resets_empty_count() -> None:
    mw = EmptyResponseRecoveryMiddleware()
    runtime = _runtime()
    update = await mw.aafter_model(
        {"messages": [AIMessage(content="你好")], "empty_response_count": 1},
        runtime,
    )
    assert update == {"empty_response_count": 0}


@pytest.mark.asyncio
async def test_summary_is_archived_once() -> None:
    memory = _FakeMemory()
    runtime = _runtime(memory)
    archive = SummaryArchiveMiddleware()
    summary = HumanMessage(
        content="保留的重要历史摘要",
        additional_kwargs={"lc_source": "summarization"},
    )
    state = {"messages": [summary]}

    first = await archive.abefore_model(state, runtime)
    assert first is not None
    second = await archive.abefore_model(
        {**state, "last_archived_summary_hash": first["last_archived_summary_hash"]},
        runtime,
    )

    assert second is None
    assert len(memory.history) == 1
    assert memory.history[0]["kind"] == "summary"