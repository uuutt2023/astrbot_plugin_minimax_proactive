"""
MiniMax API 调用模块

该模块负责与 MiniMax 大语言模型 API 进行交互，
提供对话生成功能。

作者: uuutt2023
"""

from typing import Any

import httpx

# 常量定义
DEFAULT_API_BASE = "https://api.minimax.chat/v1"
DEFAULT_MODEL = "abab6.5s-chat"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60.0


class MiniMaxAPI:
    """MiniMax API 调用类

    用于调用 MiniMax 文本对话 API，支持自定义模型参数。
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.api_key: str = config.get("api_key", "")
        self.api_base: str = config.get("api_base", DEFAULT_API_BASE)
        self.model: str = config.get("model", DEFAULT_MODEL)
        self.temperature: float = config.get("temperature", DEFAULT_TEMPERATURE)
        self.max_tokens: int = config.get("max_tokens", DEFAULT_MAX_TOKENS)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(
        self,
        prompt: str,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        if not self.is_configured:
            raise ValueError("MiniMax API Key 未配置")

        messages = self._build_messages(prompt, history, system_prompt)

        url = f"{self.api_base}/text/chatcompletion_v2"
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return self._parse_response(response.json())

    def _build_messages(
        self,
        prompt: str,
        history: list[dict[str, Any]] | None,
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
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

    def _parse_response(self, result: dict[str, Any]) -> str:
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        msg = f"MiniMax API 返回格式异常: {result}"
        raise ValueError(msg)
