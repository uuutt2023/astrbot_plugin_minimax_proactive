"""
消息发送器模块

用于发送消息的类。

作者: uuutt2023
"""

from __future__ import annotations

from typing import Any


class MessageSender:
    """消息发送器"""

    def __init__(self, plugin: Any) -> None:
        self.plugin: Any = plugin

    async def send(
        self,
        session_id: str,
        text: str,
        tts_settings: dict | None = None,
        t2i_settings: dict | None = None,
    ) -> None:
        """发送消息

        Args:
            session_id: 会话ID
            text: 消息文本
            tts_settings: TTS 设置
            t2i_settings: 文转图设置
        """
        from astrbot.api.event import MessageChain
        from astrbot.core.message.components import Plain

        # 构建消息链
        chain = MessageChain([Plain(text=text)])

        # 发送消息
        await self.plugin.context.send_message(session_id, chain)
