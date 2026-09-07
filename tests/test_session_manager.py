"""
要求
- 创建后重载仍在；
- activate 持久化；
- 每会话独立 lock；
- cancel 会 `task.cancel()`。
"""

import pytest
import asyncio
from pathlib import Path

from mini_nanobot.session.manager import SessionManager


def test_create_survives_reload(tmp_path: Path):
    manager = SessionManager(tmp_path)
    session = manager.create_session()
    reloaded = SessionManager(tmp_path)
    assert reloaded.sessions.get(session.thread_id) == session

# def test_activate_persist(tmp_path: Path):
#     manager = SessionManager(tmp_path)
#     session = manager.create_session()
#     manager.activate(session.thread_id)
#     reloaded = SessionManager(tmp_path)
#     active = reloaded.get_active()
#     assert active is not None
#     assert active.thread_id == session.thread_id
