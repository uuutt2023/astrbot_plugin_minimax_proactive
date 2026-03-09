"""
消息处理器模块
负责消息预处理，添加时间戳、发送者信息等元数据

基于 astrbot_plugin_group_chat_plus 的 message_processor.py 适配而来

重构后使用组件化架构:
- UserInfoExtractor: 用户/机器人信息提取
- TimestampFormatter: 时间戳格式化

作者: uuutt2023
参考: Him666233
版本: v1.1.0
"""

from __future__ import annotations

from typing import Any

from astrbot.api import logger

from .timestamp import TimestampFormatter
from .user_info import UserInfoExtractor

# 详细日志开关
DEBUG_MODE: bool = False


class MessageProcessor:
    """
    消息处理器

    主要功能：
    1. 添加时间戳
    2. 添加发送者信息（ID和昵称）
    3. 格式化消息便于AI理解
    4. 处理@消息提示
    5. 处理戳一戳提示

    重构后使用组件:
    - UserInfoExtractor: 用户信息提取
    - TimestampFormatter: 时间戳格式化
    """

    @staticmethod
    def add_metadata_to_message(
        event: Any,
        message_text: str,
        include_timestamp: bool = True,
        include_sender_info: bool = True,
        mention_info: dict | None = None,
        trigger_type: str | None = None,
        poke_info: dict | None = None,
        is_empty_at: bool = False,
    ) -> str:
        """
        为消息添加元数据（时间戳和发送者）

        格式与历史消息保持一致，便于AI识别：
        [时间] 发送者名字(ID:xxx): 消息内容

        Args:
            event: 消息事件
            message_text: 原始消息
            include_timestamp: 是否包含时间戳
            include_sender_info: 是否包含发送者信息
            mention_info: @别人的信息字典（如果存在）
            trigger_type: 触发方式，可选值: "at", "keyword", "ai_decision"
            poke_info: 戳一戳信息字典（如果存在）
            is_empty_at: 是否是空@消息（只有@没有其他内容）

        Returns:
            添加元数据后的文本
        """
        try:
            # 获取时间戳
            timestamp_str = ""
            if include_timestamp:
                timestamp_str = TimestampFormatter.format(event)

            # 获取发送者信息
            sender_prefix = ""
            if include_sender_info:
                sender_id = UserInfoExtractor.get_sender_id(event)
                sender_name = UserInfoExtractor.get_sender_name(event)
                sender_prefix = UserInfoExtractor.format_sender_info(sender_id, sender_name)

            # 组合格式：[时间] 发送者(ID:xxx): 消息内容
            processed_message = MessageProcessor._build_message(
                timestamp_str, sender_prefix, message_text
            )

            # 如果存在@别人的信息，添加系统提示
            if mention_info and isinstance(mention_info, dict):
                processed_message = MessageProcessor._add_mention_notice(
                    processed_message, timestamp_str, sender_prefix,
                    mention_info, message_text
                )

            # 添加戳一戳系统提示（如果存在）
            if poke_info and isinstance(poke_info, dict):
                processed_message = MessageProcessor._add_poke_notice(
                    processed_message, poke_info
                )

            # 添加发送者识别系统提示（根据触发方式）
            if include_sender_info and trigger_type:
                processed_message = MessageProcessor._add_trigger_notice(
                    processed_message, event, trigger_type, is_empty_at
                )

            return processed_message

        except Exception as e:
            logger.error(f"[MessageProcessor] 添加消息元数据时发生错误: {e}")
            return message_text

    @staticmethod
    def add_metadata_from_cache(
        message_text: str,
        sender_id: str,
        sender_name: str,
        message_timestamp: float,
        include_timestamp: bool = True,
        include_sender_info: bool = True,
        mention_info: dict | None = None,
        trigger_type: str | None = None,
        poke_info: dict | None = None,
        is_empty_at: bool = False,
    ) -> str:
        """
        使用缓存中的发送者信息为消息添加元数据

        用于缓存消息转正时，使用原始发送者的信息

        Args:
            message_text: 消息文本
            sender_id: 发送者ID（从缓存中获取）
            sender_name: 发送者名称（从缓存中获取）
            message_timestamp: 消息时间戳（从缓存中获取）
            include_timestamp: 是否包含时间戳
            include_sender_info: 是否包含发送者信息
            mention_info: @别人的信息字典（如果存在）
            trigger_type: 触发方式，可选值: "at", "keyword", "ai_decision"
            poke_info: 戳一戳信息字典（如果存在）
            is_empty_at: 是否是空@消息（只有@没有其他内容）

        Returns:
            添加元数据后的文本
        """
        try:
            # 获取时间戳
            timestamp_str = ""
            if include_timestamp:
                timestamp_str = TimestampFormatter.format_from_timestamp(message_timestamp)

            # 获取发送者信息
            sender_prefix = ""
            if include_sender_info:
                sender_prefix = UserInfoExtractor.format_sender_info(sender_id, sender_name)

            # 组合格式
            processed_message = MessageProcessor._build_message(
                timestamp_str, sender_prefix, message_text
            )

            # 如果存在@别人的信息，添加系统提示
            if mention_info and isinstance(mention_info, dict):
                processed_message = MessageProcessor._add_mention_notice(
                    processed_message, timestamp_str, sender_prefix,
                    mention_info, message_text
                )

            # 添加戳一戳系统提示（如果存在）
            if poke_info and isinstance(poke_info, dict):
                processed_message = MessageProcessor._add_poke_notice(
                    processed_message, poke_info
                )

            # 添加发送者识别系统提示（根据触发方式）
            if include_sender_info and trigger_type:
                processed_message = MessageProcessor._add_trigger_notice_from_cache(
                    processed_message, sender_id, sender_name, trigger_type, is_empty_at
                )

            return processed_message

        except Exception as e:
            logger.error(f"[MessageProcessor] 从缓存添加消息元数据时发生错误: {e}")
            return message_text

    @staticmethod
    def _build_message(timestamp_str: str, sender_prefix: str, message_text: str) -> str:
        """构建基础消息格式"""
        if timestamp_str and sender_prefix:
            return f"[{timestamp_str}] {sender_prefix}: {message_text}"
        elif timestamp_str:
            return f"[{timestamp_str}] {message_text}"
        elif sender_prefix:
            return f"{sender_prefix}: {message_text}"
        else:
            return message_text

    @staticmethod
    def _add_mention_notice(
        processed_message: str,
        timestamp_str: str,
        sender_prefix: str,
        mention_info: dict,
        message_text: str,
    ) -> str:
        """添加@指向说明"""
        mentioned_id = mention_info.get("mentioned_user_id", "")
        mentioned_name = mention_info.get("mentioned_user_name", "")

        if not mentioned_id:
            return processed_message

        mention_notice = "\n【@指向说明】这条消息通过@符号指定发送给其他用户"
        if mentioned_name:
            mention_notice += f"（被@用户：{mentioned_name}，ID：{mentioned_id}）"
        else:
            mention_notice += f"（被@用户ID：{mentioned_id}）"
        mention_notice += "，并非发给你本人。"
        mention_notice += f"\n【原始内容】{message_text}"

        # 替换原消息
        if timestamp_str and sender_prefix:
            return f"[{timestamp_str}] {sender_prefix}: {mention_notice}"
        elif timestamp_str:
            return f"[{timestamp_str}] {mention_notice}"
        elif sender_prefix:
            return f"{sender_prefix}: {mention_notice}"
        else:
            return mention_notice

    @staticmethod
    def _add_poke_notice(processed_message: str, poke_info: dict) -> str:
        """添加戳一戳提示"""
        is_poke_bot = poke_info.get("is_poke_bot", False)
        poke_sender_id = poke_info.get("sender_id", "")
        poke_sender_name = poke_info.get("sender_name", "未知用户")
        poke_target_id = poke_info.get("target_id", "")
        poke_target_name = poke_info.get("target_name", "未知用户")

        if is_poke_bot:
            poke_notice = f"\n[戳一戳提示]有人在戳你，戳你的人是{poke_sender_name}(ID:{poke_sender_id})"
            if DEBUG_MODE:
                logger.info(f"已添加戳一戳提示（戳机器人）: 戳人者={poke_sender_name}")
        else:
            poke_notice = f"\n[戳一戳提示]这是一个戳一戳消息，但不是戳你的，是{poke_sender_name}(ID:{poke_sender_id})在戳{poke_target_name}(ID:{poke_target_id})"
            if DEBUG_MODE:
                logger.info(f"已添加戳一戳提示（戳别人）: 戳人者={poke_sender_name}, 被戳者={poke_target_name}")

        return processed_message + poke_notice

    @staticmethod
    def _add_trigger_notice(
        processed_message: str,
        event: Any,
        trigger_type: str,
        is_empty_at: bool,
    ) -> str:
        """添加触发类型提示（从事件）"""
        sender_id = UserInfoExtractor.get_sender_id(event)
        sender_name = UserInfoExtractor.get_sender_name(event)
        sender_info_text = UserInfoExtractor.format_sender_info(sender_id, sender_name)

        return MessageProcessor._build_trigger_notice(
            processed_message, sender_info_text, trigger_type, is_empty_at
        )

    @staticmethod
    def _add_trigger_notice_from_cache(
        processed_message: str,
        sender_id: str,
        sender_name: str,
        trigger_type: str,
        is_empty_at: bool,
    ) -> str:
        """添加触发类型提示（从缓存）"""
        sender_info_text = UserInfoExtractor.format_sender_info(sender_id, sender_name)

        return MessageProcessor._build_trigger_notice(
            processed_message, sender_info_text, trigger_type, is_empty_at
        )

    @staticmethod
    def _build_trigger_notice(
        processed_message: str,
        sender_info_text: str,
        trigger_type: str,
        is_empty_at: bool,
    ) -> str:
        """构建触发类型提示"""
        system_notice = ""

        if trigger_type == "at":
            if is_empty_at:
                system_notice = (
                    f"\n\n[系统提示]{sender_info_text} 单独@了你，但没有附带任何消息内容。"
                    f"\n💬 就像真人收到一条无内容@消息一样，自然地回应就好——"
                    f"可以问句「？」或「怎么了，找我有事吗？」之类的话。"
                )
            else:
                system_notice = (
                    f"\n\n[系统提示]注意，现在有人在直接@你并且给你发送了这条消息，"
                    f"@你的那个人是{sender_info_text}"
                )
        elif trigger_type == "keyword":
            system_notice = (
                f"\n\n[系统提示]注意，你刚刚发现这条消息里面包含和你有关的信息，"
                f"这条消息的发送者是{sender_info_text}。"
                f"\n🔍 请仔细观察上下文和对话走向，结合发送者的实际意图，"
                f"像真人一样自然地决定怎么回复——不要只因为关键词就机械回应。"
            )
        elif trigger_type == "ai_decision":
            system_notice = f"\n\n[系统提示]注意，你看到了这条消息，发送这条消息的人是{sender_info_text}"

        if system_notice:
            if DEBUG_MODE:
                logger.info(f"已添加发送者识别提示（触发方式: {trigger_type}）")
            return processed_message + system_notice

        return processed_message


__all__ = ["MessageProcessor", "UserInfoExtractor", "TimestampFormatter"]
