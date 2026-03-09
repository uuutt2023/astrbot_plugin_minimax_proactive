"""
时间戳格式化器

负责格式化时间戳为统一格式。

作者: uuutt2023
重构自 MessageProcessor
"""

from datetime import datetime
from typing import Any

from astrbot.api import logger


class TimestampFormatter:
    """时间戳格式化器 - 将时间戳格式化为统一格式"""

    # 星期名称映射
    WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    @staticmethod
    def format(event: Any) -> str:
        """格式化时间戳（统一格式，与历史消息一致）

        格式：YYYY-MM-DD 星期几 HH:MM:SS

        Args:
            event: 消息事件

        Returns:
            格式化的时间戳，失败返回空
        """
        try:
            # 尝试从消息对象获取时间戳
            if hasattr(event, "message_obj") and hasattr(event.message_obj, "timestamp"):
                timestamp = event.message_obj.timestamp
                if timestamp:
                    return TimestampFormatter._format_from_timestamp(timestamp)

            # 如果消息对象没有时间戳，使用当前时间
            return TimestampFormatter._format_from_datetime(datetime.now())

        except Exception as e:
            logger.warning(f"[TimestampFormatter] 格式化时间戳失败: {e}")
            return ""

    @staticmethod
    def format_from_timestamp(timestamp: float) -> str:
        """从时间戳格式化

        Args:
            timestamp: Unix 时间戳

        Returns:
            格式化的时间戳
        """
        try:
            return TimestampFormatter._format_from_timestamp(timestamp)
        except Exception:
            return TimestampFormatter._format_from_datetime(datetime.now())

    @staticmethod
    def format_from_datetime(dt: datetime) -> str:
        """从 datetime 对象格式化

        Args:
            dt: datetime 对象

        Returns:
            格式化的时间戳
        """
        return TimestampFormatter._format_from_datetime(dt)

    @staticmethod
    def _format_from_timestamp(timestamp: float) -> str:
        """内部方法：从时间戳格式化"""
        dt = datetime.fromtimestamp(timestamp)
        return TimestampFormatter._format_from_datetime(dt)

    @staticmethod
    def _format_from_datetime(dt: datetime) -> str:
        """内部方法：从 datetime 对象格式化"""
        weekday = TimestampFormatter.WEEKDAY_NAMES[dt.weekday()]
        return dt.strftime(f"%Y-%m-%d {weekday} %H:%M:%S")


__all__ = ["TimestampFormatter"]
