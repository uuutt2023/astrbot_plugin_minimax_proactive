"""
帮助函数模块

提供各种辅助函数，用于消息处理、配置解析等。

作者: uuutt2023
"""

import re
from typing import Any

from astrbot.api import logger


# ==================== 消息处理 ====================


def extract_text_from_messages(messages: list[Any]) -> str:
    """从消息列表中提取文本

    Args:
        messages: 消息列表

    Returns:
        提取的文本
    """
    text = ""
    for msg in messages:
        if hasattr(msg, "text"):
            text += msg.text
        elif hasattr(msg, "get_text"):
            text += msg.get_text() or ""
    return text


def has_image_in_messages(messages: list[Any]) -> bool:
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


def format_session_status(proactive_enabled: bool, reminder_enabled: bool) -> str:
    """格式化会话状态

    Args:
        proactive_enabled: 主动对话是否启用
        reminder_enabled: 提醒功能是否启用

    Returns:
        格式化的状态字符串
    """
    proactive = "开启" if proactive_enabled else "关闭"
    reminder = "开启" if reminder_enabled else "关闭"
    return f"主动对话: {proactive}\n提醒功能: {reminder}"


def format_help_message() -> str:
    """格式化帮助信息

    Returns:
        帮助信息字符串
    """
    return "\n".join([
        "=== MiniMax 主动对话插件 ===",
        "",
        "指令: /mpro help - 显示帮助",
        "     /mpro status - 查看功能状态",
        "",
        "提醒指令:",
        "     /mpro add <时间> <内容> - 添加提醒",
        "     /mpro ls - 列出所有提醒",
        "     /mpro rm <序号> - 删除提醒",
        "     /mpro clear - 删除所有提醒",
    ])


def log_and_return_error(message: str, error: Exception) -> None:
    """记录错误日志

    Args:
        message: 错误消息前缀
        error: 异常对象
    """
    logger.error(f"[MiniMaxProactive] {message}: {error}")


def check_and_stop_request(request: Any) -> bool:
    """尝试停止请求传播

    Args:
        request: 请求对象

    Returns:
        是否成功停止
    """
    if hasattr(request, "stop_propagation"):
        request.stop_propagation()
        return True
    if hasattr(request, "terminated"):
        request.terminated = True
        return True
    return False


# ==================== 表情包检测 ====================


# Emoji 正则表达式模式
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
    "]+"
)


def is_emoji_only(text: str) -> bool:
    """检查是否只包含表情符号

    Args:
        text: 待检查的文本

    Returns:
        是否只包含表情符号
    """
    if not text:
        return True
    # 移除 emoji 后检查是否为空
    cleaned = EMOJI_PATTERN.sub('', text).strip()
    return len(cleaned) == 0
