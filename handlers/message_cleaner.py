"""
消息清理器模块
负责清理消息中的系统提示词，只保留原始用户消息

基于 astrbot_plugin_group_chat_plus 的 message_cleaner.py 适配而来

作者: uuutt2023
参考: Him666233
版本: v1.0.1
"""

from __future__ import annotations

import re
from typing import Any

from astrbot.api import logger

# 尝试导入消息组件
try:
    from astrbot.api.message_components import At, Image, Plain, Reply
except ImportError:
    try:
        from astrbot.core.message.components import At, Image, Plain, Reply
    except ImportError:
        At = None
        Plain = None
        Image = None
        Reply = None

# 尝试导入 Forward 组件
try:
    from astrbot.core.message.components import Forward
except ImportError:
    Forward = None

# 详细日志开关
DEBUG_MODE: bool = False


class MessageCleaner:
    """
    消息清理器

    主要功能：
    1. 移除系统自动添加的@消息提示词
    2. 移除决策AI相关的提示词
    3. 只保留原始用户消息内容
    4. 特殊处理主动对话提示词（保留到历史）
    """

    # 主动对话标记
    PROACTIVE_CHAT_MARKER = "[PROACTIVE_CHAT]"

    # 主动对话系统提示词的特征模式
    PROACTIVE_CHAT_PROMPT_PATTERNS = [
        r"\[🎯主动发起新话题\]",
        r"\[🔄再次尝试对话\]",
        r"\[系统提示 - 主动发起新话题场景\]",
        r"你刚刚主动发起了一个新话题",
        r"这是你主动发起的对话",
    ]

    # @消息提示词的特征模式
    AT_MESSAGE_PROMPT_PATTERNS = [
        r"注意，你正在社交媒体上.*?不要输出其他任何东西",
        r"\[当前时间:.*?\][\s\S]*?不要输出其他任何东西",
        r"用户只是通过@来唤醒你.*?不要输出其他任何东西",
        r"你友好地询问用户想要聊些什么.*?不要输出其他任何东西",
        r"\[当前时间:\d{4}-\d{2}-\d{2}\s+周[一二三四五六日]\s+\d{2}:\d{2}:\d{2}\]",
        r"\[User ID:.*?Nickname:.*?\]",
        r"\[当前情绪状态:.*?\]",
        r"注意，你正在社交媒体上中与用户进行聊天.*",
        r"用户只是通过@来唤醒你，但并未在这条消息中输入内容.*",
        r"回复要符合人设，不要太过机械化.*",
        r"你仅需要输出要回复用户的内容.*",
        r"\s*\[系统提示\]注意,现在有人在直接@你并且给你发送了这条消息，@你的那个人是.*",
        r"\s*\[系统提示\]注意，现在有人在直接@你并且给你发送了这条消息，@你的那个人是.*",
        r"\s*\[系统提示\]注意，你刚刚发现这条消息里面包含和你有关的信息，这条消息的发送者是.*",
        r"\s*\[系统提示\]注意，你看到了这条消息，发送这条消息的人是.*",
        r"\s*\[戳一戳提示\]有人在戳你，戳你的人是.*",
        r"\s*\[戳一戳提示\]这是一个戳一戳消息，但不是戳你的，是.*在戳.*",
        r"\s*\[戳过对方提示\]你刚刚戳过这条消息的发送者.*",
        r"\[系统提示\][^\n]+只是单纯@了你，没有附带任何新的消息内容。\n📋[\s\S]*?就像真人一样。",
        r"\[系统提示\][^\n]+单独@了你，但没有附带任何消息内容，[\s\S]*?之类的话。",
        r"\[系统提示\]注意，你刚刚发现这条消息里面包含和你有关的信息[\s\S]*?机械回应。",
        r"\n+\s*\[系统提示\][^\n]*",
        r"\n+\s*\[戳一戳提示\][^\n]*",
        r"\n+\s*\[戳过对方提示\][^\n]*",
        r"【当前人格设定】[\s\S]*?(?=\n\[当前时间:|\n\[User ID:|$)",
    ]

    # 决策AI提示词的特征模式
    DECISION_AI_PROMPT_PATTERNS = [
        r"=== 历史消息上下文 ===",
        r"=+ 【重要】当前新消息.*?=+",
        r"=== 当前新消息 ===",
        r"请根据历史消息.*?请开始回复",
        r"你是一个活跃、友好的群聊参与者.*?请开始判断",
        r"核心原则（重要！）：[\s\S]*?请开始回复",
        r"核心原则（重要！）：[\s\S]*?请开始判断",
        r"=== 背景信息 ===[\s\S]*?(?=\n\n|$)",
        r"💭 相关记忆：[\s\S]*?(?=\n\n|$)",
        r"=== 可用工具列表 ===[\s\S]*?(?=请根据上述对话|请开始回复|$)",
        r"当前平台共有 \d+ 个可用工具:[\s\S]*?(?=请根据上述对话|请开始回复|$)",
        r"============================================================\n*⚠️ 【当前对话对象】重要提醒 ⚠️[\s\S]*?============================================================",
        r"当前和你对话的人是.*?(?=\n|$)",
        r"当前对话的对象是.*?(?=\n|$)",
        r"【第一重要】识别当前发送者：[\s\S]*?(?=请开始回复|$)",
        r"特殊标记说明：[\s\S]*?(?=请开始回复|$)",
        r"⚠️ \*\*【关于历史中的系统提示词】重要说明\*\* ⚠️：[\s\S]*?(?=请开始回复|$)",
        r"核心原则（重要！）：[\s\S]*?(?=请开始回复|$)",
        r"⚠️ \*\*【严禁重复】必须执行的检查步骤\*\* ⚠️：[\s\S]*?(?=请开始回复|$)",
        r"关于记忆和背景信息的使用：[\s\S]*?(?=请开始回复|$)",
        r"回复要求：[\s\S]*?(?=请开始回复|$)",
        r"⛔ \*\*【严禁元叙述】特别重要！\*\* ⛔：[\s\S]*?(?=请开始回复|$)",
        r"关于【@指向说明】标记的消息：[\s\S]*?(?=请开始回复|$)",
        r"用户补充说明:[\s\S]*?(?=请开始回复|$)",
        r"请开始回复：\s*$",
        r"当前给你发消息的人是：.*?\n",
        r"请特别注意：[\s\S]*?(?=\n\n|请根据上述对话|请开始回复|$)",
        r"... 还有 \d+ 条记忆",
        r"\(这些信息可能对理解当前对话有帮助[\s\S]*?\)",
        r"\(以上是你可以调用的所有工具[\s\S]*?\)",
        r"\n*=+\n*📋 【你之前的判断记录】[\s\S]*?=+\n*",
        r"提示：保持判断的一致性，如果话题没有变化或没有新的互动需求，[\s\S]*?避免过于频繁地打扰对话。",
        r"\d{2}:\d{2}:\d{2}: [✅❌][^\n]+",
        r"【步骤9】🎭 拟人增强[\s\S]*?(?=\n|$)",
        r"🎭 检测到兴趣话题[\s\S]*?(?=\n|$)",
        r"🎭 已注入历史决策记录到提示词",
        r"\n*=+\n*🔄 【对话疲劳提示】[\s\S]*?=+\n*",
        r"\n*=+\n*🔄 【对话收尾提示】[\s\S]*?=+\n*",
        r"与当前用户的连续对话轮次:[\s\S]*?(?=\n\n|$)",
        r"你已经与这个用户连续对话了 \d+ 轮[\s\S]*?(?=\n\n|$)",
    ]

    @staticmethod
    def clean_message(message_text: str) -> str:
        """
        清理消息，移除系统添加的提示词

        ⚠️ 注意：此方法会移除所有系统提示词，包括主动对话的提示词
        如果需要保留主动对话提示词，请使用 clean_message_preserve_proactive

        Args:
            message_text: 原始消息（可能包含提示词）

        Returns:
            清理后的消息（只包含用户真实发送的内容）
        """
        if not message_text:
            return message_text

        cleaned = message_text

        # 移除@消息提示词
        for pattern in MessageCleaner.AT_MESSAGE_PROMPT_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)

        # 移除决策AI提示词
        for pattern in MessageCleaner.DECISION_AI_PROMPT_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)

        # 清理多余的分隔符
        cleaned = re.sub(r"\n*=+\n*", "\n", cleaned)

        # 清理多余的空白行
        cleaned = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned)

        # 去除首尾空白
        cleaned = cleaned.strip()

        return cleaned

    @staticmethod
    def is_proactive_chat_message(message_text: str) -> bool:
        """
        检测消息是否为主动对话消息

        Args:
            message_text: 消息文本

        Returns:
            True=主动对话消息, False=普通消息
        """
        if not message_text:
            return False

        # 检查是否包含主动对话标记
        if MessageCleaner.PROACTIVE_CHAT_MARKER in message_text:
            return True

        # 检查是否包含主动对话提示词特征
        for pattern in MessageCleaner.PROACTIVE_CHAT_PROMPT_PATTERNS:
            if re.search(pattern, message_text):
                return True

        return False

    @staticmethod
    def clean_message_preserve_proactive(message_text: str) -> str:
        """
        清理消息，但保留主动对话的系统提示词

        用于保存到官方历史时的清理，让AI能理解自己之前主动发起的对话

        Args:
            message_text: 原始消息（可能包含提示词）

        Returns:
            清理后的消息（保留主动对话提示词，移除其他系统提示词）
        """
        if not message_text:
            return message_text

        # 如果不是主动对话消息，使用普通清理
        if not MessageCleaner.is_proactive_chat_message(message_text):
            return MessageCleaner.clean_message(message_text)

        # 是主动对话消息，需要保留主动对话提示词
        cleaned = message_text

        # 移除@消息提示词
        for pattern in MessageCleaner.AT_MESSAGE_PROMPT_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)

        # 移除决策AI提示词
        for pattern in MessageCleaner.DECISION_AI_PROMPT_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)

        # 不移除主动对话提示词

        # 清理多余的分隔符
        cleaned = re.sub(r"\n*=+\n*", "\n", cleaned)

        # 清理多余的空白行
        cleaned = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned)

        # 去除首尾空白
        cleaned = cleaned.strip()

        return cleaned

    @staticmethod
    def mark_proactive_chat_message(message_text: str) -> str:
        """
        标记消息为主动对话消息

        Args:
            message_text: 原始消息

        Returns:
            带标记的消息
        """
        if not message_text:
            return message_text

        # 如果已经有标记，不重复添加
        if MessageCleaner.PROACTIVE_CHAT_MARKER in message_text:
            return message_text

        return f"{MessageCleaner.PROACTIVE_CHAT_MARKER}\n{message_text}"

    @staticmethod
    def filter_poke_text_marker(text: str) -> str:
        """
        过滤消息中的"[Poke:poke]"文本标识符

        防止用户手动输入戳一戳标识符来伪造戳一戳消息

        Args:
            text: 原始消息文本

        Returns:
            过滤后的消息文本
        """
        if not text:
            return text

        # 使用正则表达式过滤
        filtered_text = re.sub(
            r"\[\s*Poke\s*:\s*poke\s*\]", "", text, flags=re.IGNORECASE
        )

        return filtered_text.strip()

    @staticmethod
    def is_only_poke_marker(text: str) -> bool:
        """
        检查消息是否只包含"[Poke:poke]"标识符

        Args:
            text: 原始消息文本

        Returns:
            True=只有标识符, False=包含其他内容
        """
        if not text:
            return False

        cleaned = text.strip()
        pattern = r"^\[\s*Poke\s*:\s*poke\s*\]$"
        return bool(re.match(pattern, cleaned, flags=re.IGNORECASE))

    @staticmethod
    def extract_raw_message_from_event(event: Any) -> str:
        """
        从事件中提取纯净的原始消息（不含任何系统添加的内容）

        Args:
            event: 消息事件

        Returns:
            原始消息文本
        """
        try:
            # 方法1: 从消息链中提取
            if hasattr(event, "message_obj") and hasattr(event.message_obj, "message"):
                raw_parts = []
                for component in event.message_obj.message:
                    if Plain and isinstance(component, Plain):
                        if component.text is not None:
                            raw_parts.append(component.text)
                    elif At and isinstance(component, At):
                        if hasattr(component, "qq"):
                            raw_parts.append(f"[At:{component.qq}]")
                    elif Image and isinstance(component, Image):
                        raw_parts.append("[图片]")
                    elif Reply and isinstance(component, Reply):
                        reply_text = MessageCleaner._format_reply_component(component)
                        if reply_text:
                            raw_parts.append(reply_text)
                    elif Forward and isinstance(component, Forward):
                        raw_parts.append("[转发消息]")

                if raw_parts:
                    raw_message = "".join(raw_parts).strip()
                    if raw_message:
                        if DEBUG_MODE:
                            logger.info(
                                f"[MessageCleaner] 从消息链提取原始消息: {raw_message[:100]}..."
                            )
                        raw_message = MessageCleaner.filter_poke_text_marker(raw_message)
                        return raw_message

            # 方法2: 使用get_message_str
            plain_message = ""
            if hasattr(event, "get_message_str"):
                plain_message = event.get_message_str()
            elif hasattr(event, "message_str"):
                plain_message = event.message_str

            if plain_message:
                cleaned = MessageCleaner.clean_message(plain_message)
                if cleaned:
                    cleaned = MessageCleaner.filter_poke_text_marker(cleaned)
                    return cleaned

            # 方法3: 使用get_message_outline
            outline_message = ""
            if hasattr(event, "get_message_outline"):
                outline_message = event.get_message_outline()
            elif hasattr(event, "message_outline"):
                outline_message = event.message_outline

            if outline_message:
                cleaned = MessageCleaner.clean_message(outline_message)
                if cleaned:
                    cleaned = MessageCleaner.filter_poke_text_marker(cleaned)
                    return cleaned

            return ""

        except Exception as e:
            logger.error(f"[MessageCleaner] 提取原始消息失败: {e}")
            return ""

    @staticmethod
    def _format_reply_component(reply_component: Any) -> str:
        """
        格式化引用消息组件为文本表示

        Args:
            reply_component: Reply组件

        Returns:
            格式化后的引用消息文本
        """
        try:
            sender_id = None
            sender_nickname = None
            message_content = None

            if hasattr(reply_component, "sender_id"):
                sender_id = reply_component.sender_id

            if hasattr(reply_component, "sender_nickname"):
                sender_nickname = reply_component.sender_nickname
            elif hasattr(reply_component, "sender_name"):
                sender_nickname = reply_component.sender_name

            if hasattr(reply_component, "message_str"):
                message_content = reply_component.message_str
            elif hasattr(reply_component, "message"):
                message_content = reply_component.message

            if sender_nickname and sender_id and message_content:
                return f"[引用 {sender_nickname}(ID:{sender_id}): {message_content}]"
            elif sender_id and message_content:
                return f"[引用 用户(ID:{sender_id}): {message_content}]"
            elif sender_nickname and message_content:
                return f"[引用 {sender_nickname}: {message_content}]"
            elif message_content:
                return f"[引用消息: {message_content}]"
            else:
                return "[引用消息]"

        except Exception as e:
            if DEBUG_MODE:
                logger.info(f"[MessageCleaner] 格式化引用消息失败: {e}")
            return "[引用消息]"

    @staticmethod
    def is_empty_at_message(raw_message: str, is_at_message: bool) -> bool:
        """
        判断是否是纯@消息（只有@没有其他内容）

        Args:
            raw_message: 原始消息
            is_at_message: 是否是@消息

        Returns:
            True=纯@消息，False=有其他内容
        """
        if not is_at_message:
            return False

        # 移除所有@标记
        without_at = re.sub(r"\[At:\d+\]", "", raw_message)
        without_at = without_at.strip()

        is_empty = len(without_at) == 0

        if is_empty:
            if DEBUG_MODE:
                logger.info("[MessageCleaner] 检测到纯@消息（无其他内容）")

        return is_empty

    @staticmethod
    def process_cached_message_images(message_text: str) -> tuple:
        """
        处理缓存消息中的图片

        概率筛选失败时，缓存的消息需要特殊处理：
        - 如果消息只包含图片（纯图片），不缓存
        - 如果消息是文本+图片，移除图片标记，只保留文本
        - 如果消息只有文本，直接保留

        Args:
            message_text: 原始消息文本（可能包含 [图片] 标记）

        Returns:
            (should_cache, processed_text):
            - should_cache: 是否应该缓存
            - processed_text: 处理后的文本
        """
        if not message_text:
            return False, ""

        # 移除所有图片标记
        text_without_images = re.sub(r"\[图片\]", "", message_text)
        text_without_images = text_without_images.strip()

        # 判断是否是纯图片消息
        if not text_without_images:
            has_image = "[图片]" in message_text
            if has_image:
                if DEBUG_MODE:
                    logger.info("[MessageCleaner] 检测到纯图片消息，丢弃不缓存")
                return False, ""
            else:
                return False, ""

        # 检查是否有图片被移除
        has_image = "[图片]" in message_text
        if has_image:
            if DEBUG_MODE:
                logger.info(
                    f"[MessageCleaner] 移除图片标记，保留文本: {text_without_images[:100]}..."
                )
            return True, text_without_images
        else:
            return True, message_text
