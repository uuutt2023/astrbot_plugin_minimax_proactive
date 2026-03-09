"""
LLM 拦截处理器

处理 LLM 请求拦截和读空气判断逻辑。

作者: uuutt2023
"""

from __future__ import annotations

import random
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..business.constants import (
    Defaults,
    EmojiGateKeys,
    MessageKeys,
    ProactiveKeys,
    ReadAirKeys,
)
from ..utils import (
    check_and_stop_request,
    extract_text_from_messages,
    has_image_in_messages,
    sanitize_history,
)
from ..utils import (
    is_emoji_only as check_emoji_only,
)


class LLMInterceptor:
    """LLM 拦截处理器"""

    def __init__(
        self,
        llm: Any,
        sender: Any,
        core: Any,
    ) -> None:
        self._llm: Any = llm
        self._sender: Any = sender
        self._core: Any = core

    async def handle_llm_request(self, event: AstrMessageEvent, request: Any, session_id: str, cfg: dict[str, Any]) -> bool:
        """处理 LLM 对话请求"""
        if not cfg.get(ProactiveKeys.USE_MINIMAX_FOR_RESPONSE, False):
            return False

        messages = event.get_messages()
        if not messages:
            return False

        user_text = "".join(
            getattr(msg, "text", "") or getattr(msg, "get_text", lambda: "")() or ""
            for msg in messages
        )
        if not user_text:
            return False

        logger.info(f"[MiniMaxProactive] 使用LLM处理对话: {session_id}")
        try:
            ctx = await self._core._get_context(session_id)
            if not ctx:
                return False

            history = sanitize_history(ctx["history"])
            history.append({"role": "user", "content": user_text})
            response = (await self._llm.chat(user_text, history, ctx["system_prompt"])).strip()

            if response and response != "[object Object]":
                if self._sender:
                    await self._sender.send(
                        session_id, response,
                        cfg.get(MessageKeys.TTS_SETTINGS, {}),
                        cfg.get(MessageKeys.T2I_SETTINGS, {})
                    )
                if request:
                    getattr(request, "stop_propagation", lambda: None)() or setattr(request, "terminated", True)
                logger.info(f"[MiniMaxProactive] LLM对话完成: {session_id}")
                return True
        except Exception as e:
            logger.error(f"[MiniMaxProactive] LLM对话失败: {e}")
        return False

    async def handle_read_air(self, event: AstrMessageEvent, request: Any, session_id: str, cfg: dict[str, Any]) -> bool:
        """处理读空气判断"""
        messages = event.get_messages()
        if not messages:
            return True

        user_text = extract_text_from_messages(messages)
        has_image = has_image_in_messages(messages)
        is_emoji_only_msg = has_image and (not user_text.strip() or check_emoji_only(user_text))

        # 表情包守门员
        if is_emoji_only_msg and cfg.get(EmojiGateKeys.EMOJI_GATE_ENABLED, False):
            if random.randint(1, 100) > cfg.get(EmojiGateKeys.EMOJI_GATE_RATE, Defaults.EMOJI_GATE_RATE):
                check_and_stop_request(request)
                logger.info(f"[MiniMaxProactive] 表情包守门员阻止回复: {session_id}")
                return False
            logger.info(f"[MiniMaxProactive] 表情包守门员放行: {session_id}")

        # 读空气判断
        read_air_cfg = cfg.get(ReadAirKeys.READ_AIR_SETTINGS, {})
        if not read_air_cfg.get(ReadAirKeys.ENABLE_READ_AIR, False):
            return True

        if not user_text:
            return True

        logger.info(f"[MiniMaxProactive] 读空气判断: {session_id}")
        try:
            from ..prompts import DEFAULT_READ_AIR
            system_prompt = read_air_cfg.get(ReadAirKeys.READ_AIR_PROMPT, DEFAULT_READ_AIR)
            llm_response = await self._llm.chat("", [{"role": "user", "content": f"请判断以下消息是否需要回复：{user_text}"}], system_prompt)
            chat_result = llm_response.strip().upper()

            should_respond = "YES" in chat_result or "应该" in chat_result or "需要" in chat_result
            if should_respond:
                logger.info(f"[MiniMaxProactive] 读空气判断需要回复: {session_id}")
                return True
            else:
                check_and_stop_request(request)
                logger.info(f"[MiniMaxProactive] 读空气判断不需要回复: {session_id}")
                return False
        except Exception as e:
            logger.error(f"[MiniMaxProactive] 读空气判断失败: {e}")
            return True


__all__ = ["LLMInterceptor"]
