"""
上下文提供者

负责获取对话上下文，包括历史消息、人格设定等。
使用依赖注入解耦 AstrBot 内部 API。

作者: uuutt2023
重构自 ProactiveCore
"""

from typing import Any

import orjson

from astrbot.api import logger

from ..llm import ImageCaptionUtils
from ..prompts import DEFAULT_IMAGE_DESC
from ..utils.text_utils import replace_image_with_text


class ContextProvider:
    """上下文提供者 - 负责获取对话上下文"""

    def __init__(self, context: Any, llm: Any, storage: Any) -> None:
        self._context = context
        self._llm = llm
        self._storage = storage
        self._image_caption_utils = ImageCaptionUtils(storage=storage, timeout=30)
        self._image_caption_utils.initialize()

    async def get_context(self, session_id: str) -> dict | None:
        """获取对话上下文

        Args:
            session_id: 会话ID

        Returns:
            包含 conv_id, history, system_prompt 的字典，或 None
        """
        try:
            conv_mgr = getattr(self._context, "conversation_manager", None)
            if not conv_mgr:
                return None

            conv_id = await conv_mgr.get_curr_conversation_id(session_id)
            if not conv_id:
                conv_id = await conv_mgr.new_conversation(session_id)
            if not conv_id:
                return None

            conv = await conv_mgr.get_conversation(session_id, conv_id)

            # 获取历史消息
            history = self._extract_history(conv)

            # 获取人格设定
            system_prompt = await self._get_persona_prompt(session_id, conv)

            if not system_prompt:
                logger.error("[ContextProvider] 无法加载人格设定")
                return None

            return {"conv_id": conv_id, "history": history, "system_prompt": system_prompt}

        except Exception as e:
            logger.warning(f"[ContextProvider] 获取上下文失败: {e}")
            return None

    def _extract_history(self, conv: Any) -> list:
        """提取历史消息"""
        history = []
        if conv and conv.history:
            try:
                history = (
                    orjson.loads(conv.history)
                    if isinstance(conv.history, str)
                    else conv.history
                )
            except Exception:
                pass
        return history

    async def _get_persona_prompt(self, session_id: str, conv: Any) -> str:
        """获取人格设定提示词"""
        persona_mgr = getattr(self._context, "persona_manager", None)

        # 优先使用会话绑定的人格
        if conv and conv.persona_id and persona_mgr:
            persona = await persona_mgr.get_persona(conv.persona_id)
            if persona:
                return persona.system_prompt

        # 其次使用默认人格
        if persona_mgr:
            default = await persona_mgr.get_default_persona_v3(umo=session_id)
            if default:
                return default.get("prompt", "")

        return ""

    async def process_image_descriptions(
        self,
        history: list,
        session_id: str,
        image_desc_cfg: dict | None = None,
    ) -> list:
        """处理历史消息中的表情包转述

        Args:
            history: 历史消息列表
            session_id: 会话ID
            image_desc_cfg: 表情包转述配置

        Returns:
            处理后的历史消息列表
        """
        if not image_desc_cfg or not image_desc_cfg.get("enable_image_desc"):
            return history

        # 获取提示词
        image_desc_prompt = image_desc_cfg.get("image_desc_prompt") or DEFAULT_IMAGE_DESC

        # 获取超时设置
        timeout = image_desc_cfg.get("image_desc_timeout", 30)
        self._image_caption_utils.timeout = timeout

        processed_history = []

        for i, msg in enumerate(history):
            if isinstance(msg, dict):
                content = msg.get("content", "")

                # 检查是否包含表情包标记
                if "[表情]" in content or "[图片]" in content:
                    # 尝试获取图片URL
                    image_url = msg.get("image_url") or msg.get("image") or msg.get("url")

                    if image_url:
                        # 使用工具类描述图片
                        description = await self._image_caption_utils.describe_image(
                            llm=self._llm,
                            image_url=image_url,
                            prompt=image_desc_prompt,
                            session_id=session_id
                        )

                        # 定期清理过期缓存
                        if i > 0 and i % 10 == 0:
                            self._image_caption_utils.cleanup_expired()

                        if description:
                            # 替换表情包标记为转述文本
                            content = replace_image_with_text(content, description.strip())
                            logger.info(f"[ContextProvider] 图片转述: {description[:50]}...")
                        else:
                            # 转述失败，替换为占位符
                            content = replace_image_with_text(content, "图片")

                    msg["content"] = content

            processed_history.append(msg)

        return processed_history


__all__ = ["ContextProvider"]
