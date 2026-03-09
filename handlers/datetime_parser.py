"""
日期时间解析器

负责解析各种时间字符串格式。

作者: uuutt2023
重构自 ReminderManager
"""

import datetime


class DateTimeParser:
    """日期时间解析器 - 解析各种时间字符串格式"""

    @staticmethod
    def parse(datetime_str: str) -> datetime.datetime | None:
        """解析时间字符串

        支持格式:
        - YYYY-MM-DD HH:MM
        - HH:MM (当天或明天的这个时间)

        Args:
            datetime_str: 时间字符串

        Returns:
            datetime 对象，或 None 如果解析失败
        """
        try:
            # 标准化分隔符
            datetime_str = datetime_str.strip().replace("：", ":")

            # 尝试完整日期时间格式
            return datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

        # 尝试仅时间格式 (HH:MM)
        try:
            if ":" in datetime_str and "-" not in datetime_str:
                today = datetime.datetime.now()
                hour, minute = map(int, datetime_str.split(":"))
                dt = today.replace(hour=hour, minute=minute, second=0)
                # 如果时间已过，则设置为明天
                if dt < today:
                    dt += datetime.timedelta(days=1)
                return dt
        except Exception:
            pass

        return None

    @staticmethod
    def format(dt: datetime.datetime) -> str:
        """格式化 datetime 为字符串

        Args:
            dt: datetime 对象

        Returns:
            格式化后的字符串 (YYYY-MM-DD HH:MM)
        """
        return dt.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def get_repeat_string(repeat: str) -> str:
        """获取重复描述字符串

        Args:
            repeat: 重复类型 (daily, weekly, monthly, yearly, none)

        Returns:
            描述字符串
        """
        if repeat == "daily":
            return "，每天重复"
        elif repeat == "weekly":
            return "，每周重复"
        elif repeat == "monthly":
            return "，每月重复"
        elif repeat == "yearly":
            return "，每年重复"
        return ""


__all__ = ["DateTimeParser"]
