"""
时间处理工具模块

提供时间、时区相关的通用工具函数。

作者: uuutt2023
"""

from datetime import datetime
from zoneinfo import ZoneInfo


def is_quiet_time(quiet_hours: str, timezone: ZoneInfo | None = None) -> bool:
    """检查是否为免打扰时段

    Args:
        quiet_hours: 格式 "HH-HH"，如 "1-7"
        timezone: 时区

    Returns:
        bool: 是否在免打扰时段
    """
    try:
        start_h, end_h = quiet_hours.split("-")
        start, end = int(start_h), int(end_h)
        now = datetime.now(timezone).hour

        if start <= end:
            return start <= now < end
        return now >= start or now < end
    except Exception:
        return False
