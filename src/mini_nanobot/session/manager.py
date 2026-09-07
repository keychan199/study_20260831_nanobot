"""
参考类
SessionInfo(thread_id, title, created_at, updated_at)
PendingEvent  # 本章可先定义，enqueue/drain 下一章再用
RunStatus: idle | running | cancelling
SessionManager
"""
from pathlib import Path
from datetime import datetime



class SessionManager:
    def __init__(self, path: Path):
        self.path = path
        self.sessions = {}
        self.next_thread_id = 0

    def create_session(self):
        session = SessionInfo(
            thread_id=self.next_thread_id,
            title="",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.sessions[session.thread_id] = session
        self.next_thread_id += 1
        return self.sessions[session.thread_id]


class SessionInfo:
    def __init__(self, thread_id: int, title: str, created_at: datetime, updated_at: datetime):
        self.thread_id = thread_id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at


class PendingEvent:
    pass


class RunStatus:
    pass

