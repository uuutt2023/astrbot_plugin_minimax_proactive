"""
辅助函数模块

提供各种辅助函数，包括文本处理、消息处理等。

作者: uuutt2023
"""


# ==================== 消息处理 ====================


def extract_text_from_messages(messages) -> str:
    """从消息列表中提取文本

    Args:
        messages: 消息列表

    Returns:
        提取的文本内容
    """
    text = ""
    for msg in messages:
        if hasattr(msg, "text"):
            text += msg.text
        elif hasattr(msg, "get_text"):
            text += msg.get_text() or ""
    return text


def has_image_in_messages(messages) -> bool:
    """检查消息列表中是否包含图片

    Args:
        messages: 消息列表

    Returns:
        是否包含图片
    """
    for msg in messages:
        if hasattr(msg, "image_urls") and msg.image_urls:
            return True
        if hasattr(msg, "image_url") and msg.image_url:
            return True
    return False


def is_emoji_only(text: str) -> bool:
    """检查文本是否只包含表情符号

    Args:
        text: 待检查的文本

    Returns:
        是否只包含表情符号
    """
    if not text:
        return False

    # 常见的表情符号范围
    emoji_ranges = [
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F300, 0x1F5FF),  # Symbols & Pictographs
        (0x1F680, 0x1F6FF),  # Transport & Map
        (0x1F1E0, 0x1F1FF),  # Flags
        (0x2600, 0x26FF),    # Miscellaneous
        (0x2700, 0x27BF),    # Dingbats
    ]

    # 过滤掉空白字符
    filtered = "".join(c for c in text if not c.isspace())

    if not filtered:
        return False

    # 检查是否都是表情符号
    for char in filtered:
        is_emoji = False
        for start, end in emoji_ranges:
            if start <= ord(char) <= end:
                is_emoji = True
                break
        if not is_emoji:
            return False

    return True


def check_and_stop_request(request) -> None:
    """阻止请求继续传播

    Args:
        request: 请求对象
    """
    if request is not None:
        if hasattr(request, "stop_propagation"):
            request.stop_propagation()
        elif hasattr(request, "terminated"):
            request.terminated = True


def log_and_return_error(message: str, error: Exception) -> str:
    """记录错误并返回错误消息

    Args:
        message: 错误消息前缀
        error: 异常对象

    Returns:
        格式化的错误消息
    """
    from astrbot.api import logger

    logger.error(f"[MiniMaxProactive] {message}: {error}")
    return f"{message}: {str(error)}"


# ==================== 格式输出 ====================


def format_session_status(proactive_enabled: bool, reminder_enabled: bool) -> str:
    """格式化会话状态

    Args:
        proactive_enabled: 主动对话是否启用
        reminder_enabled: 提醒功能是否启用

    Returns:
        格式化的状态字符串
    """
    status = []
    status.append("=" * 20)
    status.append("MiniMax Proactive 状态")
    status.append("=" * 20)
    status.append(f"主动对话: {'✅ 启用' if proactive_enabled else '❌ 禁用'}")
    status.append(f"提醒功能: {'✅ 启用' if reminder_enabled else '❌ 禁用'}")
    status.append("=" * 20)
    return "\n".join(status)


def format_help_message() -> str:
    """格式化帮助信息

    Returns:
        格式化的帮助字符串
    """
    from ..prompts import DEFAULT_HELP
    return DEFAULT_HELP
