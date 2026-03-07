"""
LLM 调用模块

该模块负责与大语言模型交互，支持两种模式：
1. 使用 AstrBot 内置的 LLM Provider
2. 使用自定义的 MiniMax API

作者: uuutt2023
"""

from typing import Any

import httpx

from astrbot.api import logger
from astrbot.core.provider.entities import LLMResponse

from .decorators import debug, get_debug_logger

# MiniMax API 常量
DEFAULT_API_BASE = "https://api.minimax.chat/v1"
DEFAULT_MODEL = "abab6.5s-chat"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60.0


class LLMCaller:
    """LLM 调用器

    支持两种调用方式：
    1. 使用 AstrBot 内置 Provider（通过 context）
    2. 使用自定义 MiniMax API
    """

    def __init__(self, context, config: dict[str, Any]) -> None:
        self._context = context
        self._config = config

        # MiniMax API 配置
        self._miniMax_config = config.get("minimax_settings", {}) or {}
        self._api_key = self._miniMax_config.get("api_key", "")
        self._api_base = self._miniMax_config.get("base_url", DEFAULT_API_BASE)
        self._model = self._miniMax_config.get("model", DEFAULT_MODEL)
        self._temperature = self._miniMax_config.get("temperature", DEFAULT_TEMPERATURE)
        self._max_tokens = self._miniMax_config.get("max_tokens", DEFAULT_MAX_TOKENS)
        
        # 调试模式 - 从配置获取并同步到全局DebugLog
        self._debug = config.get("debug_mode", False)
        get_debug_logger().enabled = self._debug
        
        if self._debug:
            logger.info("[MiniMaxProactive][DEBUG] LLMCaller初始化:")
            logger.info(f"[MiniMaxProactive][DEBUG]   - selected_provider: {self._config.get('selected_provider', '')}")
            logger.info(f"[MiniMaxProactive][DEBUG]   - use_minimax_for_response: {self._config.get('use_minimax_for_response', False)}")
            logger.info(f"[MiniMaxProactive][DEBUG]   - debug_mode: {self._debug}")
            logger.info(f"[MiniMaxProactive][DEBUG]   - minimax配置: api_key={'已配置' if self._api_key else '未配置'}, model={self._model}")

    @property
    def debug_mode(self) -> bool:
        """调试模式"""
        return self._debug

    @property
    def use_astrbot_provider(self) -> bool:
        """是否使用 AstrBot 内置 Provider
        
        逻辑：
        - 如果选择了AstrBot provider (selected_provider不为空)，优先使用AstrBot
        - 但如果 use_minimax_for_response 为True，则使用MiniMax API
        """
        # 检查是否配置了AstrBot provider
        has_provider = bool(self._config.get("selected_provider", ""))
        # 检查是否强制使用MiniMax
        use_minimax = self._config.get("use_minimax_for_response", False)
        
        # 如果选择了AstrBot provider且没有强制使用MiniMax，则用AstrBot
        result = has_provider and not use_minimax
        
        if self._debug:
            logger.info("[MiniMaxProactive][DEBUG] use_astrbot_provider计算:")
            logger.info(f"[MiniMaxProactive][DEBUG]   - has_provider: {has_provider}")
            logger.info(f"[MiniMaxProactive][DEBUG]   - use_minimax: {use_minimax}")
            logger.info(f"[MiniMaxProactive][DEBUG]   - result: {result}")
        
        return result
    
    @property
    def use_minimax_for_response(self) -> bool:
        """是否使用MiniMax API进行对话"""
        # 如果没有配置MiniMax API，返回False
        if not self.is_minimax_configured:
            return False
        # 如果开启了use_minimax_for_response，使用MiniMax
        return self._config.get("use_minimax_for_response", False)
    
    @property
    def selected_provider(self) -> str:
        """获取用户选择的provider名称"""
        return self._config.get("selected_provider", "")

    @property
    def is_minimax_configured(self) -> bool:
        """MiniMax API 是否已配置"""
        return bool(self._api_key)

    @property
    def is_configured(self) -> bool:
        """是否有可用的 LLM（兼容旧接口）"""
        return self.available

    @property
    def available(self) -> bool:
        """是否有可用的 LLM"""
        if self.use_astrbot_provider:
            return True  # 使用内置 Provider，总是可用
        if self.use_minimax_for_response:
            return self.is_minimax_configured  # 使用MiniMax API
        return False

    @debug("chat() 调用")
    async def chat(
        self,
        prompt: str,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """调用 LLM 获取回复

        Args:
            prompt: 用户输入
            history: 对话历史
            system_prompt: 系统提示词
            session_id: 会话 ID

        Returns:
            LLM 回复文本
        """
        if self._debug:
            logger.info("[MiniMaxProactive][DEBUG] chat() 调用:")
            logger.info(f"[MiniMaxProactive][DEBUG]   - use_astrbot_provider: {self.use_astrbot_provider}")
            logger.info(f"[MiniMaxProactive][DEBUG]   - use_minimax_for_response: {self.use_minimax_for_response}")
            logger.info(f"[MiniMaxProactive][DEBUG]   - is_minimax_configured: {self.is_minimax_configured}")
        
        if self.use_astrbot_provider:
            if self._debug:
                logger.info(f"[MiniMaxProactive][DEBUG] 使用 AstrBot Provider: {self.selected_provider}")
            return await self._chat_with_astrbot(
                prompt, history, system_prompt, session_id
            )
        else:
            if self._debug:
                logger.info(f"[MiniMaxProactive][DEBUG] 使用 MiniMax API: {self._model}")
            return await self._chat_with_minimax(prompt, history, system_prompt)

    async def _chat_with_astrbot(
        self,
        prompt: str,
        history: list[dict[str, Any]] | None,
        system_prompt: str | None,
        session_id: str | None,
    ) -> str:
        """使用 AstrBot 内置 Provider 调用 LLM"""
        try:
            # 获取当前使用的 Provider
            # 如果用户通过_special选择了特定provider，优先使用
            selected = self.selected_provider
            if selected:
                provider = self._context.get_using_provider(selected)
            else:
                provider = self._context.get_using_provider(session_id or "")

            if not provider:
                logger.warning("[MiniMaxProactive] 未找到可用的 LLM Provider")
                raise ValueError("未配置 LLM Provider")

            # 构建消息列表
            messages = self._build_messages(prompt, history, system_prompt)

            # 调用 LLM
            response: LLMResponse = await provider.text_chat(
                prompt=prompt,
                contexts=messages,
                system_prompt=system_prompt,
            )

            # 解析回复 - 使用 result_chain 获取文本内容
            if response and response.result_chain:
                # result_chain 是 MessageChain 类型
                return str(response.result_chain)

            return ""

        except Exception as e:
            logger.error(f"[MiniMaxProactive] AstrBot LLM 调用失败: {e}")
            raise

    async def _chat_with_minimax(
        self,
        prompt: str,
        history: list[dict[str, Any]] | None,
        system_prompt: str | None,
    ) -> str:
        """使用 MiniMax API 调用 LLM"""
        if not self.is_minimax_configured:
            raise ValueError("MiniMax API Key 未配置")

        messages = self._build_messages(prompt, history, system_prompt)

        url = f"{self._api_base}/text/chatcompletion_v2"
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return self._parse_minimax_response(response.json())

    def _build_messages(
        self,
        prompt: str,
        history: list[dict[str, Any]] | None,
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        """构建消息列表"""
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            for msg in history:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": prompt})
        return messages

    def _parse_minimax_response(self, result: dict[str, Any]) -> str:
        """解析 MiniMax API 响应"""
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        msg = f"MiniMax API 返回格式异常: {result}"
        raise ValueError(msg)

    @debug("should_respond() 判断是否需要回复")
    async def should_respond(
        self,
        user_text: str,
        read_air_prompt: str,
        session_id: str | None = None,
        provider_name: str | None = None,
    ) -> bool:
        """判断是否需要回复（读空气功能）

        Args:
            user_text: 用户消息
            read_air_prompt: 判断提示词
            session_id: 会话 ID
            provider_name: 指定的provider名称

        Returns:
            是否需要回复
        """
        if not self.available and not provider_name:
            return True  # 无法判断时默认回复

        try:
            # 如果指定了provider，优先使用
            if provider_name:
                provider = self._context.get_using_provider(provider_name)
                if provider:
                    return await self._should_respond_with_provider(
                        provider, user_text, read_air_prompt
                    )
            
            # 否则使用默认方式
            result = await self.chat(
                prompt=f"请判断以下消息是否需要回复：{user_text}",
                history=[],
                system_prompt=read_air_prompt,
                session_id=session_id,
            )
            result = result.strip().upper()

            should_respond = "YES" in result or "应该" in result or "需要" in result
            return should_respond

        except Exception as e:
            logger.error(f"[MiniMaxProactive] 读空气判断失败: {e}")
            return True  # 判断失败时默认回复

    async def _should_respond_with_provider(
        self,
        provider,
        user_text: str,
        read_air_prompt: str,
    ) -> bool:
        """使用指定provider判断是否需要回复"""
        messages = [{"role": "system", "content": read_air_prompt}]
        messages.append({"role": "user", "content": f"请判断以下消息是否需要回复：{user_text}"})

        try:
            response: LLMResponse = await provider.text_chat(
                prompt=user_text,
                contexts=messages,
                system_prompt=read_air_prompt,
            )

            if response and response.result_chain:
                result = str(response.result_chain).strip().upper()
                return "YES" in result or "应该" in result or "需要" in result

            return True

        except Exception as e:
            logger.error(f"[MiniMaxProactive] Provider读空气判断失败: {e}")
            return True

    @debug("describe_image() 描述图片")
    async def describe_image(
        self,
        image_url: str,
        prompt: str,
        session_id: str | None = None,
        provider_name: str | None = None,
    ) -> str | None:
        """描述图片（表情包转述功能）

        Args:
            image_url: 图片URL或base64
            prompt: 描述提示词
            session_id: 会话 ID
            provider_name: 指定的provider名称

        Returns:
            图片描述文本，失败返回None
        """
        if not self.available and not provider_name:
            logger.warning("[MiniMaxProactive] LLM不可用，无法描述图片")
            return None

        try:
            # 如果指定了provider，优先使用
            if provider_name:
                provider = self._context.get_using_provider(provider_name)
                if provider:
                    return await self._describe_image_with_provider(
                        provider, image_url, prompt
                    )
            
            if self.use_astrbot_provider:
                return await self._describe_image_with_astrbot(
                    image_url, prompt, session_id
                )
            else:
                # MiniMax 多模态 API
                return await self._describe_image_with_minimax(image_url, prompt)

        except Exception as e:
            logger.error(f"[MiniMaxProactive] 图片描述失败: {e}")
            return None

    async def _describe_image_with_provider(
        self,
        provider,
        image_url: str,
        prompt: str,
    ) -> str | None:
        """使用指定provider描述图片"""
        try:
            # 构建多模态消息
            messages = []
            
            if prompt:
                messages.append({"role": "system", "content": prompt})
            
            image_content = {"type": "image_url"}
            if image_url.startswith("data:") or "," in image_url[:50]:
                image_content["image_url"] = {"url": image_url}
            else:
                image_content["image_url"] = {"url": image_url}
            
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "请描述这张图片的内容。"},
                    image_content
                ]
            })

            response: LLMResponse = await provider.text_chat(
                prompt="描述这张图片",
                contexts=messages,
                system_prompt=prompt,
            )

            if response and response.result_chain:
                return str(response.result_chain)

            return None

        except Exception as e:
            logger.error(f"[MiniMaxProactive] Provider图片描述失败: {e}")
            return None

    async def _describe_image_with_astrbot(
        self,
        image_url: str,
        prompt: str,
        session_id: str | None,
    ) -> str | None:
        """使用 AstrBot Provider 描述图片"""
        try:
            # 如果用户通过_special选择了特定provider，优先使用
            selected = self.selected_provider
            if selected:
                provider = self._context.get_using_provider(selected)
            else:
                provider = self._context.get_using_provider(session_id or "")
            
            if not provider:
                logger.warning("[MiniMaxProactive] 未找到 LLM Provider")
                return None

            # 构建多模态消息
            messages = []
            
            # 添加系统提示
            if prompt:
                messages.append({"role": "system", "content": prompt})
            
            # 添加图片消息 - 使用 URL 或 base64
            image_content = {"type": "image_url"}
            if image_url.startswith("data:") or "," in image_url[:50]:
                # base64 图片
                image_content["image_url"] = {"url": image_url}
            else:
                # URL 图片
                image_content["image_url"] = {"url": image_url}
            
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "请描述这张图片的内容。"},
                    image_content
                ]
            })

            # 调用多模态 LLM
            response: LLMResponse = await provider.text_chat(
                prompt="描述这张图片",
                contexts=messages,
                system_prompt=prompt,
            )

            if response and response.result_chain:
                return str(response.result_chain)

            return None

        except Exception as e:
            logger.error(f"[MiniMaxProactive] AstrBot 图片描述失败: {e}")
            return None

    async def _describe_image_with_minimax(
        self,
        image_url: str,
        prompt: str,
    ) -> str | None:
        """使用 MiniMax API 描述图片"""
        if not self.is_minimax_configured:
            logger.warning("[MiniMaxProactive] MiniMax API 未配置")
            return None

        # MiniMax 多模态 API 端点
        url = f"{self._api_base}/v1/text/chatcompletion_v2"
        
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # 构建多模态消息
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请描述这张图片的内容。"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            
            return None
