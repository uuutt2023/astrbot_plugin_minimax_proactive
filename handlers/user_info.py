"""
用户信息提取器

负责从消息事件中提取用户和机器人相关信息。

作者: uuutt2023
重构自 MessageProcessor
"""

import re
from typing import Any

from astrbot.api import logger

# 尝试导入消息组件
try:
    from astrbot.api.message_components import At
except ImportError:
    try:
        from astrbot.core.message.components import At
    except ImportError:
        At = None


class UserInfoExtractor:
    """用户信息提取器 - 从消息事件中提取用户和机器人信息"""

    @staticmethod
    def get_sender_id(event: Any) -> str:
        """获取发送者ID"""
        try:
            if hasattr(event, "get_sender_id"):
                return event.get_sender_id()
            if hasattr(event, "sender") and hasattr(event.sender, "user_id"):
                return str(event.sender.user_id)
            if hasattr(event, "user_id"):
                return str(event.user_id)
            return "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def get_sender_name(event: Any) -> str:
        """获取发送者昵称"""
        try:
            if hasattr(event, "get_sender_name"):
                return event.get_sender_name()
            if hasattr(event, "sender") and hasattr(event.sender, "nickname"):
                return event.sender.nickname or ""
            if hasattr(event, "sender") and hasattr(event.sender, "name"):
                return event.sender.name or ""
            return ""
        except Exception:
            return ""

    @staticmethod
    def get_bot_id(event: Any) -> str:
        """获取机器人ID"""
        try:
            if hasattr(event, "get_self_id"):
                return event.get_self_id()
            if hasattr(event, "self_id"):
                return str(event.self_id)
            if hasattr(event, "bot_id"):
                return str(event.bot_id)
            return ""
        except Exception:
            return ""

    @staticmethod
    def is_message_from_bot(event: Any) -> bool:
        """判断消息是否来自bot自己

        Args:
            event: 消息事件

        Returns:
            True=bot自己的消息，False=其他人
        """
        sender_id = UserInfoExtractor.get_sender_id(event)
        bot_id = UserInfoExtractor.get_bot_id(event)

        is_bot = sender_id == bot_id
        if is_bot:
            logger.info(
                f"[UserInfoExtractor] 检测到机器人自己的消息,将忽略: sender_id={sender_id}, bot_id={bot_id}"
            )
        return is_bot

    @staticmethod
    def is_at_message(event: Any, debug_mode: bool = False) -> bool:
        """判断消息是否@了bot

        Args:
            event: 消息事件
            debug_mode: 调试模式开关

        Returns:
            True=@了bot，False=没有@
        """
        if not At:
            return False

        # 方法1: 检查消息链中是否有At组件指向机器人
        if hasattr(event, "message_obj") and hasattr(event.message_obj, "message"):
            bot_id = UserInfoExtractor.get_bot_id(event)
            message_chain = event.message_obj.message

            for component in message_chain:
                if At and isinstance(component, At):
                    if hasattr(component, "qq") and str(component.qq) == str(bot_id):
                        if debug_mode:
                            logger.info("检测到@机器人的消息（At组件）")
                        return True

        # 方法2: 检查消息文本中是否包含@机器人
        try:
            bot_id = UserInfoExtractor.get_bot_id(event)
            bot_name = None

            if hasattr(event, "unified_msg_origin"):
                origin_parts = str(event.unified_msg_origin).split(":")
                if len(origin_parts) > 0:
                    bot_name = origin_parts[0]

            message_text = ""
            if hasattr(event, "get_message_str"):
                message_text = event.get_message_str()
            elif hasattr(event, "message_str"):
                message_text = event.message_str

            if message_text:
                # 检查 @机器人ID
                if f"@{bot_id}" in message_text:
                    if debug_mode:
                        logger.info(f"检测到@机器人的消息（文本@ID: @{bot_id}）")
                    return True

                # 检查 @机器人名称
                if bot_name:
                    pattern = rf"@{re.escape(bot_name)}(?:[^a-zA-Z0-9_]|$)"
                    if re.search(pattern, message_text):
                        if debug_mode:
                            logger.info(f"检测到@机器人的消息（文本@名称: @{bot_name}）")
                        return True
        except Exception as e:
            if debug_mode:
                logger.info(f"文本@检测时出错: {e}")

        return False

    @staticmethod
    def format_sender_info(sender_id: str, sender_name: str = "") -> str:
        """格式化发送者信息

        Args:
            sender_id: 发送者ID
            sender_name: 发送者昵称（可选）

        Returns:
            格式化的发送者信息，如 "用户名(ID:123)" 或 "用户(ID:123)"
        """
        if sender_name:
            return f"{sender_name}(ID:{sender_id})"
        else:
            return f"用户(ID:{sender_id})"


__all__ = ["UserInfoExtractor"]
