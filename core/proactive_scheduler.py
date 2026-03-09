"""
主动聊天调度器

负责主动聊天的触发调度逻辑。
使用 APScheduler 进行定时任务管理。

作者: uuutt2023
重构自 ProactiveCore
"""

import random
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from astrbot.api import logger

from ..business.constants import (
    Defaults,
    ProactiveKeys,
    ScheduleKeys,
    StorageKeys,
)


class ProactiveScheduler:
    """主动聊天调度器 - 负责触发调度逻辑"""

    def __init__(
        self,
        scheduler: Any,
        storage: Any,
        timezone: Any,
    ) -> None:
        self._scheduler = scheduler
        self._storage = storage
        self._timezone = timezone

    def schedule_trigger(
        self,
        session_id: str,
        cfg: dict,
        callback: Callable,
    ) -> None:
        """调度下次触发

        Args:
            session_id: 会话ID
            cfg: 会话配置
            callback: 触发回调函数
        """
        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        min_interval = (
            int(schedule.get(ScheduleKeys.MIN_INTERVAL_MINUTES, Defaults.MIN_INTERVAL_MINUTES))
            * 60
        )
        max_interval = max(
            min_interval,
            int(schedule.get(ScheduleKeys.MAX_INTERVAL_MINUTES, Defaults.MAX_INTERVAL_MINUTES))
            * 60,
        )

        # 添加随机延迟
        delay = random.randint(min_interval, max_interval)

        # 添加调度任务
        self._scheduler.add_job(
            callback,
            session_id,
            0,
            min_interval,
            max_interval,
        )

        # 保存下次触发时间
        data = self._storage.get_sync(session_id, {})
        data[StorageKeys.NEXT_TRIGGER_TIME] = time.time() + delay
        self._storage.set_sync(session_id, data)

    def schedule_idle_trigger(
        self,
        session_id: str,
        cfg: dict,
        callback: Callable,
    ) -> None:
        """调度沉默触发

        Args:
            session_id: 会话ID
            cfg: 会话配置
            callback: 触发回调函数
        """
        idle_minutes = cfg.get(
            ProactiveKeys.GROUP_IDLE_TRIGGER_MINUTES,
            Defaults.GROUP_IDLE_TRIGGER_MINUTES,
        )
        self._scheduler.add_job(callback, session_id, idle_minutes * 60)

    def calculate_delay(self, cfg: dict) -> int:
        """计算触发延迟（秒）

        Args:
            cfg: 会话配置

        Returns:
            延迟秒数
        """
        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        min_interval = (
            int(schedule.get(ScheduleKeys.MIN_INTERVAL_MINUTES, Defaults.MIN_INTERVAL_MINUTES))
            * 60
        )
        max_interval = max(
            min_interval,
            int(schedule.get(ScheduleKeys.MAX_INTERVAL_MINUTES, Defaults.MAX_INTERVAL_MINUTES))
            * 60,
        )
        return random.randint(min_interval, max_interval)

    def is_quiet_time(self, cfg: dict) -> bool:
        """检查是否在免打扰时段

        Args:
            cfg: 会话配置

        Returns:
            是否在免打扰时段
        """
        from ..utils.time_utils import is_quiet_time
        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        return is_quiet_time(
            schedule.get(ScheduleKeys.QUIET_HOURS, Defaults.QUIET_HOURS),
            self._timezone,
        )

    def reached_limit(self, cfg: dict, count: int) -> bool:
        """检查是否达到触发上限

        Args:
            cfg: 会话配置
            count: 当前未回复计数

        Returns:
            是否达到上限
        """
        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        max_count = schedule.get(
            ScheduleKeys.MAX_UNANSWERED_TIMES, Defaults.MAX_UNANSWERED_TIMES
        )
        if max_count > 0 and count >= max_count:
            logger.info(f"[ProactiveScheduler] 达到上限 ({count}/{max_count})")
            return True
        return False

    def build_prompt(
        self,
        cfg: dict,
        count: int,
        default_private_prompt: str,
        default_group_prompt: str,
    ) -> str:
        """构建主动聊天 Prompt

        Args:
            cfg: 会话配置
            count: 未回复计数
            default_private_prompt: 默认私聊提示词
            default_group_prompt: 默认群聊提示词

        Returns:
            格式化后的提示词
        """
        prompt = cfg.get(ProactiveKeys.PROACTIVE_PROMPT, "")
        if not prompt:
            # 根据会话类型选择默认 Prompt
            session_type = cfg.get("session_type", "private")
            if session_type == "group":
                prompt = default_group_prompt
            else:
                prompt = default_private_prompt

        # 替换变量
        now_str = datetime.now(self._timezone).strftime("%Y年%m月%d日 %H:%M")
        prompt = prompt.replace("{{unanswered_count}}", str(count)).replace(
            "{{current_time}}", now_str
        )
        return prompt


__all__ = ["ProactiveScheduler"]
