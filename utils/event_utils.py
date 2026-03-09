"""
事件处理工具模块

提供事件解析、消息提取等通用工具函数。

作者: uuutt2023
"""

from typing import Any

from astrbot.api.event import AstrMessageEvent


def extract_event_from_args(*args, **kwargs) -> tuple[AstrMessageEvent | None, Any | None]:
    """从参数中提取事件和请求对象

    兼容不同版本的参数传递方式。

    Args:
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        (event, request) 元组
    """
    event = None
    request = None

    # 从位置参数中查找事件
    for arg in args:
        if isinstance(arg, AstrMessageEvent):
            event = arg
            break

    # 从关键字参数中获取
    if not event:
        event = kwargs.get("event")

    # 获取请求对象
    request = kwargs.get("request") or (args[1] if len(args) > 1 else None)

    return event, request


def extract_user_text(messages: list[Any]) -> str:
    """从消息列表中提取用户文本

    Args:
        messages: 消息列表

    Returns:
        提取的文本
    """
    if not messages:
        return ""

    user_text = ""
    for msg in messages:
        if hasattr(msg, "text"):
            user_text += msg.text
        elif hasattr(msg, "get_text"):
            user_text += msg.get_text() or ""

    return user_text


def has_image(messages: list[Any]) -> bool:
    """检查消息列表中是否包含图片

    Args:
        messages: 消息列表

    Returns:
        是否包含图片
    """
    for msg in messages:
        if hasattr(msg, "image") and msg.image:
            return True
        if hasattr(msg, "get_image"):
            img = msg.get_image()
            if img:
                return True
    return False
