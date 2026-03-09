"""
服务模块

提供依赖注入和服务创建功能。

作者: uuutt2023
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# ==================== 协议定义 ====================


@runtime_checkable
class StorageProtocol(Protocol):
    """存储服务协议"""
    async def load(self) -> dict: ...
    async def save(self) -> None: ...
    @property
    def data(self) -> dict: ...


@runtime_checkable
class SchedulerProtocol(Protocol):
    """调度器服务协议"""
    @property
    def timezone(self): ...
    def add_job(self, func: Any, session_id: str, delay_seconds: int, min_delay: int = 30, max_delay: int = 900) -> None: ...


@runtime_checkable
class LLMProtocol(Protocol):
    """LLM 服务协议"""
    @property
    def available(self) -> bool: ...
    async def chat(self, prompt: str, history: list, system_prompt: str) -> str: ...


@runtime_checkable
class MessageSenderProtocol(Protocol):
    """消息发送器协议"""
    async def send(self, session_id: str, text: str, tts_settings: dict | None = None, t2i_settings: dict | None = None) -> None: ...


@runtime_checkable
class ConfigProviderProtocol(Protocol):
    """配置提供者协议"""
    @property
    def llm_settings(self) -> dict: ...
    def get_session_config(self, session_id: str) -> dict | None: ...


# ==================== 服务容器 ====================


class ProactiveServices:
    """简化服务容器"""

    def __init__(
        self,
        storage: Any = None,
        scheduler: Any = None,
        llm: Any = None,
        config_provider: Any = None,
        message_sender: Any = None,
        context: Any = None,
    ) -> None:
        self.storage = storage
        self.scheduler = scheduler
        self.llm = llm
        self.config_provider = config_provider
        self.message_sender = message_sender
        self.context = context

    def get_session_config(self, session_id: str) -> dict | None:
        return self.config_provider.get_session_config(session_id) if self.config_provider else None


# ==================== 便捷函数 ====================


def create_services(
    context: Any,
    data_dir: Path,
    plugin_config: dict[str, Any] | None = None,
    timezone: str = "UTC",
    plugin: Any = None,
) -> tuple[ProactiveServices, dict[str, Any]]:
    """创建所有服务"""
    from ..business.config_manager import ConfigManager
    from ..handlers.messager import MessageSender
    from ..llm.caller import LLMCaller
    from ..storage.scheduler import SchedulerManager
    from ..storage.storage import Storage

    # 创建配置
    config = plugin_config or context.get_config().get("minimax_proactive", {}) or {}
    config_provider = ConfigManager(config)
    llm_settings = config_provider.llm_settings

    # 创建服务
    storage = Storage(data_dir / "session_data.json")
    scheduler = SchedulerManager()
    scheduler.timezone = timezone
    scheduler.start()

    # LLM 配置
    factory_config = {
        "minimax_settings": llm_settings.get("minimax_settings", {}),
        "use_astrbot_provider": llm_settings.get("use_astrbot_provider", ""),
        "selected_provider": llm_settings.get("selected_provider", ""),
        "use_minimax_for_response": llm_settings.get("use_minimax_for_response", False),
        "debug_mode": llm_settings.get("debug_mode", False),
    }
    if plugin_config:
        factory_config.update(plugin_config)

    llm = LLMCaller(context, factory_config)
    message_sender = MessageSender(plugin) if plugin else None

    # 组装服务
    services = ProactiveServices(
        storage=storage,
        scheduler=scheduler,
        llm=llm,
        config_provider=config_provider,
        message_sender=message_sender,
        context=context,
    )

    components = {
        "storage": storage,
        "scheduler": scheduler,
        "llm": llm,
        "config_provider": config_provider,
        "message_sender": message_sender,
    }

    return services, components


__all__ = [
    "StorageProtocol",
    "SchedulerProtocol",
    "LLMProtocol",
    "MessageSenderProtocol",
    "ConfigProviderProtocol",
    "ProactiveServices",
    "create_services",
]
