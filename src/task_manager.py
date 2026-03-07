"""
任务管理模块

提供任务调度相关的辅助函数。

作者: uuutt2023
"""

import time
from typing import Any

from .constants import (
    ConfigKeys,
    Defaults,
    ScheduleKeys,
)


def calculate_schedule_intervals(cfg: dict[str, Any]) -> tuple[int, int]:
    """计算调度间隔

    Args:
        cfg: 会话配置

    Returns:
        (最小间隔秒数, 最大间隔秒数)
    """
    schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
    min_i = (
        int(schedule.get(ScheduleKeys.MIN_INTERVAL_MINUTES, Defaults.MIN_INTERVAL_MINUTES))
        * 60
    )
    max_i = max(
        min_i,
        int(schedule.get(ScheduleKeys.MAX_INTERVAL_MINUTES, Defaults.MAX_INTERVAL_MINUTES))
        * 60,
    )
    return min_i, max_i


def calculate_next_trigger_time(min_i: int, max_i: int) -> tuple[float, int]:
    """计算下次触发时间和延迟

    Args:
        min_i: 最小间隔秒数
        max_i: 最大间隔秒数

    Returns:
        (下次触发时间戳, 延迟秒数)
    """
    import random

    delay = random.randint(min_i, max_i)
    next_time = time.time() + delay
    return next_time, delay


def should_setup_auto_trigger(
    cfg: dict[str, Any],
    session_id: str,
    message_times: dict[str, float],
    start_time: float,
) -> bool:
    """检查是否应该设置自动触发

    Args:
        cfg: 会话配置
        session_id: 会话ID
        message_times: 消息时间字典
        start_time: 插件启动时间

    Returns:
        是否应该设置自动触发
    """
    auto = cfg.get(ScheduleKeys.AUTO_TRIGGER_SETTINGS, {})
    if not auto.get(ScheduleKeys.ENABLE_AUTO_TRIGGER):
        return False

    minutes = auto.get(
        ScheduleKeys.AUTO_TRIGGER_AFTER_MINUTES, Defaults.AUTO_TRIGGER_AFTER_MINUTES
    )
    if minutes <= 0:
        return False

    # 检查是否已有消息
    if session_id in message_times:
        return False

    elapsed = time.time() - start_time
    return elapsed >= minutes * 60


def get_session_ids_from_storage(storage_data: dict) -> list[str]:
    """从存储数据中获取会话ID列表

    Args:
        storage_data: 存储数据字典

    Returns:
        会话ID列表
    """
    return list(storage_data.keys())


def is_session_config_valid(cfg: dict[str, Any] | None) -> bool:
    """检查会话配置是否有效

    Args:
        cfg: 会话配置

    Returns:
        配置是否有效
    """
    return cfg is not None and cfg.get(ConfigKeys.ENABLE)
