"""
调度管理器

处理自动触发和任务调度的逻辑。

作者: uuutt2023
"""

from __future__ import annotations

import time
from typing import Any

from astrbot.api import logger

from ..business.constants import (
    ConfigKeys,
    Defaults,
    ScheduleKeys,
    StorageKeys,
)


class SchedulerManager:
    """调度管理器"""

    def __init__(
        self,
        config_mgr: Any,
        storage: Any,
        scheduler: Any,
        core: Any,
        start_time: float,
    ) -> None:
        self._config_mgr = config_mgr
        self._storage = storage
        self._scheduler = scheduler
        self._core = core
        self._start_time = start_time

    def _calc_interval(self, cfg: dict) -> tuple[int, int]:
        """计算调度间隔"""
        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        min_i = int(schedule.get(ScheduleKeys.MIN_INTERVAL_MINUTES, Defaults.MIN_INTERVAL_MINUTES)) * 60
        max_i = max(min_i, int(schedule.get(ScheduleKeys.MAX_INTERVAL_MINUTES, Defaults.MAX_INTERVAL_MINUTES)) * 60)
        return min_i, max_i

    async def restore_jobs(self) -> None:
        """恢复保存的任务"""
        now = time.time()
        count = 0

        for session_id, data in self._storage.data.items():
            cfg = self._config_mgr.get_session_config(session_id)
            if not cfg:
                continue

            next_time = data.get(StorageKeys.NEXT_TRIGGER_TIME, 0)
            if not next_time or next_time <= now:
                continue

            delay = int(next_time - now)
            min_i, max_i = self._calc_interval(cfg)
            self._scheduler.add_job(self._core.check_and_chat, session_id, delay, min_i, max_i)
            count += 1

        logger.info(f"[MiniMaxProactive] 恢复 {count} 个任务")

    async def setup_auto_triggers(self) -> None:
        """设置自动触发"""
        logger.info("[MiniMaxProactive] 检查自动触发...")

        # 私聊会话
        for cfg in self._config_mgr.private_sessions:
            if cfg.get(ConfigKeys.ENABLE) and cfg.get(ConfigKeys.SESSION_ID):
                await self._setup_single_auto(cfg, f"default:FriendMessage:{cfg[ConfigKeys.SESSION_ID]}")

        # 群聊会话
        for cfg in self._config_mgr.group_sessions:
            if cfg.get(ConfigKeys.ENABLE) and cfg.get(ConfigKeys.SESSION_ID):
                await self._setup_single_auto(cfg, f"default:GroupMessage:{cfg[ConfigKeys.SESSION_ID]}")

        # 全局私聊自动触发
        private_default = self._config_mgr.private_default_settings
        if private_default.get(ConfigKeys.ENABLE) and private_default.get(ScheduleKeys.AUTO_TRIGGER_SETTINGS, {}).get(ScheduleKeys.ENABLE_AUTO_TRIGGER):
            logger.info("[MiniMaxProactive] 私聊全局自动触发已启用")

        # 全局群聊自动触发
        group_default = self._config_mgr.group_default_settings
        if group_default.get(ConfigKeys.ENABLE) and group_default.get(ScheduleKeys.AUTO_TRIGGER_SETTINGS, {}).get(ScheduleKeys.ENABLE_AUTO_TRIGGER):
            logger.info("[MiniMaxProactive] 群聊全局自动触发已启用")

        logger.info("[MiniMaxProactive] 自动触发检查完成")

    async def _setup_single_auto(self, cfg: dict, session_id: str) -> None:
        """设置单个自动触发"""
        auto = cfg.get(ScheduleKeys.AUTO_TRIGGER_SETTINGS, {})
        if not auto.get(ScheduleKeys.ENABLE_AUTO_TRIGGER):
            return

        minutes = auto.get(ScheduleKeys.AUTO_TRIGGER_AFTER_MINUTES, Defaults.AUTO_TRIGGER_AFTER_MINUTES)
        if minutes <= 0 or session_id in self._core._message_times:
            return

        elapsed = time.time() - self._start_time
        if elapsed < minutes * 60:
            return

        min_i, max_i = self._calc_interval(cfg)
        self._scheduler.add_job(self._core.check_and_chat, session_id, 0, min_i, max_i)


__all__ = ["SchedulerManager"]
