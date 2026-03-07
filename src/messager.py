"""
消息发送模块

该模块负责发送消息，包括文本和语音(TTS)。
使用 AstrBot 官方 API。

作者: uuutt2023
"""

import asyncio

from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageChain


class MessageSender:
    """消息发送器 - 使用 AstrBot 官方 API"""

    def __init__(self, plugin) -> None:
        self._plugin = plugin
        self._context = plugin.context

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
            text: 文本内容
            tts_settings: TTS配置
            t2i_settings: 文转图配置
        """
        tts_conf = tts_settings or {}
        t2i_conf = t2i_settings or {}

        # TTS 发送
        is_tts = await self._send_tts(session_id, text, tts_conf)

        should_send_text = not is_tts or tts_conf.get("always_send_text", True)
        if not should_send_text:
            return

        # 文转图检查 - 文字过长时转换为图片
        if t2i_conf.get("enable_t2i") and len(text) >= t2i_conf.get(
            "t2i_char_threshold", 500
        ):
            await self._send_as_image(session_id, text, t2i_conf)
            return

        # 直接发送文本消息
        await self._send_text(session_id, text)

    async def _send_tts(self, session_id: str, text: str, settings: dict) -> bool:
        """发送TTS语音 - 使用 AstrBot 官方 TTS 提供商"""
        if not settings.get("enable_tts", True):
            return False

        # 使用 AstrBot 官方 TTS 提供商
        provider = getattr(self._context, "get_using_tts_provider", None)
        if not provider:
            return False

        tts = provider(umo=session_id)
        if not tts:
            return False

        audio = await tts.get_audio(text)
        if not audio:
            return False

        # 使用官方 API 发送语音
        from astrbot.core.message.components import Record

        if audio:
            record = (
                Record.fromURL(audio)
                if audio.startswith("http")
                else Record(file=audio)
            )
            chain = MessageChain([record])
            await self._context.send_message(session_id, chain)
        await asyncio.sleep(0.5)
        return True

    async def _send_text(self, session_id: str, text: str) -> None:
        """发送文本消息 - 使用官方 API"""
        chain = MessageChain([Plain(text=text)])
        await self._context.send_message(session_id, chain)

    async def _send_as_image(self, session_id: str, text: str, settings: dict) -> None:
        """发送文转图消息"""
        try:
            # 使用 AstrBot 官方 text_to_image 方法
            # 可选：使用自定义 HTML 模板
            template = settings.get("html_template", "")

            if template:
                # 使用自定义模板
                url = await self._plugin.html_render(
                    template, {"content": text}, options=settings.get("t2i_options", {})
                )
            else:
                # 使用默认模板
                url = await self._plugin.text_to_image(text)

            if url:
                from astrbot.core.message.components import Image

                img = Image.fromURL(url)
                chain = MessageChain([img])
                await self._context.send_message(session_id, chain)
        except Exception as e:
            # 如果文转图失败，回退到文本发送
            from astrbot.api import logger

            logger.warning(f"[MiniMaxProactive] 文转图失败: {e}")
            await self._send_text(session_id, text)
