from __future__ import annotations

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from .config import load_config, AppConfig
from .prompts import build_system_prompt
from .tools import BASIC_TOOLS

def build_llm(cfg: AppConfig) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=cfg.provider.api_key,
        base_url=cfg.provider.api_base,
        model=cfg.provider.model,
        temperature=cfg.provider.temperature,
        max_tokens=cfg.provider.max_tokens,
        timeout=cfg.provider.timeout_seconds,
    )

def build_agent(cfg: AppConfig | None = None) -> CompiledStateGraph:
    cfg = cfg or load_config()
    llm = build_llm(cfg)
    return create_agent(
        model=llm,
        tools=BASIC_TOOLS,
        system_prompt=build_system_prompt(),
        name="react_agent",
    )