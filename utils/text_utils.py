"""
文本处理工具模块

提供文本处理相关的通用工具函数。

作者: uuutt2023
"""

from __future__ import annotations

import math
import random
import re
from typing import Any

# ==================== 常量定义 ====================

# 默认分段标点
DEFAULT_SPLIT_WORDS = ["。", "？", "！", "~", "…"]
DEFAULT_SPLIT_REGEX = r".*?[。？！~…\n]+|.+$"

# ==================== 文本分段 ====================


def split_text(text: str, settings: dict[str, Any]) -> list[str]:
    """分段文本

    Args:
        text: 待分段的文本
        settings: 分段配置

    Returns:
        分段后的文本列表
    """
    mode = settings.get("split_mode", "regex")

    if mode == "words":
        words = settings.get("split_words", DEFAULT_SPLIT_WORDS)
        if not words:
            return [text]

        escaped = sorted([re.escape(w) for w in words], key=len, reverse=True)
        pattern = f"(.*?({'|'.join(escaped)})|.+$)"
        segments = re.findall(pattern, text, re.DOTALL)

        result: list[str] = []
        for seg in segments:
            if isinstance(seg, tuple):
                content = seg[0]
                if isinstance(content, str) and content.strip():
                    result.append(content)
            elif seg and seg.strip():
                result.append(seg)
        return result if result else [text]
    else:
        pattern = settings.get("regex", DEFAULT_SPLIT_REGEX)
        try:
            segments = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
        except re.error:
            segments = re.findall(DEFAULT_SPLIT_REGEX, text, re.DOTALL | re.MULTILINE)
        return [s for s in segments if s.strip()]


# ==================== 历史消息处理 ====================


def sanitize_history(history: list[dict[str, Any] | object]) -> list[dict[str, Any]]:
    """清洗历史消息，转换为标准格式

    Args:
        history: 原始历史消息列表

    Returns:
        清洗后的消息列表
    """
    result: list[dict[str, Any]] = []
    for msg in history:
        if hasattr(msg, "to_dict"):
            msg = msg.to_dict()  # type: ignore
        elif not isinstance(msg, dict):
            continue

        content = msg.get("content")
        if isinstance(content, list):
            text = ""
            for seg in content:
                if isinstance(seg, dict):
                    text += seg.get("text", "")
                elif hasattr(seg, "text"):
                    text += getattr(seg, "text", "")
                elif isinstance(seg, str):
                    text += seg
            msg["content"] = text
        elif not isinstance(content, str):
            msg["content"] = str(content) if content else ""

        result.append(msg)
    return result


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
    cleaned = EMOJI_PATTERN.sub("", text).strip()
    return len(cleaned) == 0


# ==================== 发送间隔计算 ====================


DEFAULT_INTERVAL_MIN = 1.5
DEFAULT_INTERVAL_MAX = 3.5
DEFAULT_INTERVAL_STR = f"{DEFAULT_INTERVAL_MIN}, {DEFAULT_INTERVAL_MAX}"


def calc_interval(text: str, settings: dict[str, Any]) -> float:
    """计算发送间隔

    Args:
        text: 待发送的文本
        settings: 间隔配置

    Returns:
        发送间隔（秒）
    """
    method = settings.get("interval_method", "random")

    if method == "log":
        base = float(settings.get("log_base", 1.8))
        count = (
            len(text.split())
            if all(ord(c) < 128 for c in text)
            else len([c for c in text if c.isalnum()])
        )
        return random.uniform(
            math.log(count + 1, base), math.log(count + 1, base) + 0.5
        )

    try:
        interval_str = settings.get("interval", DEFAULT_INTERVAL_STR)
        interval = [float(x) for x in interval_str.replace(" ", "").split(",")]
        if len(interval) != 2:
            interval = [DEFAULT_INTERVAL_MIN, DEFAULT_INTERVAL_MAX]
    except Exception:
        interval = [DEFAULT_INTERVAL_MIN, DEFAULT_INTERVAL_MAX]

    return random.uniform(interval[0], interval[1])


# ==================== 会话ID解析 ====================

# 会话ID部分数量常量
SESSION_ID_PARTS_MIN = 3
SESSION_ID_PARTS_MAX = 3

# 消息类型常量
MSG_TYPE_FRIEND = "FriendMessage"
MSG_TYPE_GROUP = "GroupMessage"
MSG_TYPE_PRIVATE = "PrivateMessage"
MSG_TYPE_GUILD = "GuildMessage"
MESSAGE_TYPES = [MSG_TYPE_FRIEND, MSG_TYPE_GROUP, MSG_TYPE_PRIVATE, MSG_TYPE_GUILD]

# 会话类型
SESSION_TYPE_PRIVATE = "private"
SESSION_TYPE_GROUP = "group"
SESSION_TYPE_UNKNOWN = "unknown"


def parse_session_id(session_id: str) -> tuple[str, str, str] | None:
    """解析会话ID

    格式: platform:message_type:target_id

    Args:
        session_id: 会话ID字符串

    Returns:
        (platform, message_type, target_id) 或 None
    """
    if not isinstance(session_id, str):
        return None

    # 尝试查找消息类型
    for msg_type in MESSAGE_TYPES:
        pattern = f":{msg_type}:"
        idx = session_id.find(pattern)
        if idx != -1:
            return session_id[:idx], msg_type, session_id[idx + len(pattern) :]

    # 尝试按冒号分割
    parts = session_id.split(":")
    if len(parts) == SESSION_ID_PARTS_MIN:
        return parts[0], parts[1], parts[2]
    if len(parts) > SESSION_ID_PARTS_MIN:
        return ":".join(parts[:-2]), parts[-2], parts[-1]
    return None


def get_session_type(session_id: str) -> str:
    """获取会话类型

    Args:
        session_id: 会话ID

    Returns:
        "private" | "group" | "unknown"
    """
    parsed = parse_session_id(session_id)
    if not parsed:
        return SESSION_TYPE_UNKNOWN

    _, msg_type, _ = parsed

    if "Friend" in msg_type or "Private" in msg_type:
        return SESSION_TYPE_PRIVATE
    if "Group" in msg_type:
        return SESSION_TYPE_GROUP
    return SESSION_TYPE_UNKNOWN


def format_log(session_id: str, session_config: dict[str, Any] | None = None) -> str:
    """格式化日志

    Args:
        session_id: 会话ID
        session_config: 会话配置

    Returns:
        格式化的日志字符串
    """
    parsed = parse_session_id(session_id)
    if not parsed:
        return session_id

    _, msg_type, target_id = parsed

    # 判断会话类型
    if "Friend" in msg_type or "Private" in msg_type:
        type_str = "私聊"
    elif "Group" in msg_type:
        type_str = "群聊"
    else:
        type_str = "未知"

    # 获取会话名称
    name = ""
    if session_config:
        name = session_config.get("_session_name", "")

    result = f"{type_str} {target_id}"
    if name:
        result += f" ({name})"
    return result


def replace_image_with_text(
    content: str,
    replacement: str,
) -> str:
    """将消息内容中的表情包标记替换为转述文本

    Args:
        content: 原始消息内容
        replacement: 转述文本

    Returns:
        替换后的消息内容
    """
    # 常见的表情包标记
    markers = ["[表情]", "[图片]", "[image]", "[pic]", "表情", "图片"]

    result = content
    for marker in markers:
        if marker in result:
            result = result.replace(marker, f"[{replacement}]")

    return result
