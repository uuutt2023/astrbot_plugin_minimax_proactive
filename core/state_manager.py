"""
状态管理器

负责管理会话状态的并发安全读写。
使用 asyncio.Lock 保护并发访问。

作者: uuutt2023
重构自 ProactiveCore
"""

import asyncio
import time
from typing import Any

from ..business.constants import StorageKeys


class StateManager:
    """状态管理器 - 负责会话状态的并发安全管理"""

    def __init__(self, storage: Any) -> None:
        self._storage = storage
        self._lock = asyncio.Lock()
        self._message_times: dict[str, float] = {}
        self._logged: set[str] = set()

    async def record_message(self, session_id: str) -> None:
        """记录消息到达，用于调度触发"""
        async with self._lock:
            now = time.time()
            self._message_times[session_id] = now

            # 初始化或更新存储状态
            data = self._storage.get_sync(session_id, {})
            if (
                data.get(StorageKeys.LAST_TIME, 0) == 0
                or data.get(StorageKeys.UNANSWERED_COUNT, 0) != 0
            ):
                self._storage.set_sync(
                    session_id,
                    {StorageKeys.LAST_TIME: now, StorageKeys.UNANSWERED_COUNT: 0},
                )

    async def should_log(self, session_id: str) -> bool:
        """检查是否应该记录日志（每会话只记录一次）"""
        async with self._lock:
            if session_id not in self._logged:
                self._logged.add(session_id)
                return True
            return False

    def get_message_time(self, session_id: str) -> float | None:
        """获取会话最后消息时间"""
        return self._message_times.get(session_id)

    async def get_unanswered_count(self, session_id: str) -> int:
        """获取未回复计数"""
        async with self._lock:
            return self._storage.get_sync(session_id, {}).get(
                StorageKeys.UNANSWERED_COUNT, 0
            )

    async def increment_unanswered(self, session_id: str) -> int:
        """递增未回复计数，返回新值"""
        async with self._lock:
            data = self._storage.get_sync(session_id, {})
            count = data.get(StorageKeys.UNANSWERED_COUNT, 0) + 1
            data[StorageKeys.UNANSWERED_COUNT] = count
            self._storage.set_sync(session_id, data)
            return count

    async def reset_unanswered(self, session_id: str) -> None:
        """重置未回复计数"""
        async with self._lock:
            data = self._storage.get_sync(session_id, {})
            data[StorageKeys.UNANSWERED_COUNT] = 0
            self._storage.set_sync(session_id, data)

    async def set_next_trigger_time(self, session_id: str, delay: float) -> None:
        """设置下次触发时间"""
        async with self._lock:
            data = self._storage.get_sync(session_id, {})
            data[StorageKeys.NEXT_TRIGGER_TIME] = time.time() + delay
            self._storage.set_sync(session_id, data)

    def get_session_data(self, session_id: str) -> dict:
        """获取会话数据（非锁保护，仅读取）"""
        return self._storage.get_sync(session_id, {})

    def set_session_data(self, session_id: str, data: dict) -> None:
        """设置会话数据（非锁保护，仅写入）"""
        self._storage.set_sync(session_id, data)


__all__ = ["StateManager"]
