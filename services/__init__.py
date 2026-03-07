"""
服务模块

包含服务接口定义和工厂。

作者: uuutt2023
"""

from pathlib import Path
from typing import Any, Callable, Protocol

from ..src import ConfigManager
from ..libs import SchedulerManager, Storage
from ..src.llm import LLMCaller
from ..src.messager import MessageSender


# ==================== 协议定义 ====================


class StorageProtocol(Protocol):
    """存储服务协议"""

    async def load(self) -> dict: ...
    async def save(self) -> None: ...
    def get_sync(self, key: str, default: Any = None) -> Any: ...
    def set_sync(self, key: str, value: Any) -> None: ...
    @property
    def data(self) -> dict: ...


class SchedulerProtocol(Protocol):
    """调度器服务协议"""

    @property
    def timezone(self): ...

    def add_job(
        self,
        func,
        session_id: str,
        delay_seconds: int,
        min_delay: int = 30,
        max_delay: int = 900,
    ) -> None: ...


class LLMProtocol(Protocol):
    """LLM 服务协议"""

    @property
    def available(self) -> bool: ...

    async def chat(self, prompt: str, history: list, system_prompt: str) -> str: ...
    
    async def describe_image(
        self,
        image_url: str,
        prompt: str,
        session_id: str | None = None,
        provider_name: str | None = None,
    ) -> str | None: ...


class MessageSenderProtocol(Protocol):
    """消息发送器协议"""

    async def send(
        self,
        session_id: str,
        text: str,
        tts_settings: dict | None = None,
        t2i_settings: dict | None = None,
    ) -> None: ...


class ContextProtocol(Protocol):
    """AstrBot 上下文协议"""

    @property
    def conversation_manager(self) -> Any: ...
    @property
    def persona_manager(self) -> Any: ...

    async def send_message(self, session_id: str, chain: Any) -> None: ...


class ConfigProviderProtocol(Protocol):
    """配置提供者协议"""

    @property
    def llm_settings(self) -> dict: ...
    
    def get_session_config(self, session_id: str) -> dict | None: ...


class ProactiveServices:
    """主动对话服务容器 - 依赖注入容器"""

    def __init__(
        self,
        storage: StorageProtocol,
        scheduler: SchedulerProtocol,
        llm: LLMProtocol,
        context: ContextProtocol,
        config_provider: ConfigProviderProtocol,
        message_sender: MessageSenderProtocol | None = None,
    ) -> None:
        self.storage = storage
        self.scheduler = scheduler
        self.llm = llm
        self.context = context
        self.config_provider = config_provider
        self.message_sender = message_sender

    def get_session_config(self, session_id: str) -> dict | None:
        """获取会话配置"""
        return self.config_provider.get_session_config(session_id)


# ==================== 通用工厂 ====================


class ServiceFactory:
    """通用服务工厂"""

    _creators: dict[str, Callable[..., Any]] = {}

    @classmethod
    def register(cls, name: str, creator: Callable[..., Any]) -> None:
        """注册服务创建器"""
        cls._creators[name] = creator

    @classmethod
    def create(cls, name: str, *args, **kwargs) -> Any:
        """创建服务"""
        creator = cls._creators.get(name)
        if not creator:
            raise ValueError(f"未注册的服务: {name}")
        return creator(*args, **kwargs)

    @classmethod
    def get_registered_services(cls) -> list[str]:
        """获取已注册的服务列表"""
        return list(cls._creators.keys())


# 注册默认服务创建器
ServiceFactory.register("llm", lambda ctx, cfg: LLMCaller(ctx, cfg))
ServiceFactory.register(
    "storage", lambda data_dir: Storage(data_dir / "session_data.json")
)
ServiceFactory.register(
    "scheduler",
    lambda timezone="UTC": (
        setattr((s := SchedulerManager()), "timezone", timezone) or s.start() or s
    ),
)
ServiceFactory.register("message_sender", lambda plugin: MessageSender(plugin))
ServiceFactory.register(
    "config_provider",
    lambda ctx, cfg=None: (
        ConfigManager(cfg or ctx.get_config().get("minimax_proactive", {}) or {})
    ),
)


# ==================== 兼容层 ====================


class LLMFactory:
    """LLM 服务工厂 (兼容)"""

    @staticmethod
    def create(context: Any, config: dict[str, Any]) -> LLMProtocol:
        return ServiceFactory.create("llm", context, config)


class StorageFactory:
    """存储服务工厂 (兼容)"""

    @staticmethod
    def create(data_dir: Path) -> StorageProtocol:
        return ServiceFactory.create("storage", data_dir)


class SchedulerFactory:
    """调度服务工厂 (兼容)"""

    @staticmethod
    def create(timezone: str = "UTC") -> SchedulerProtocol:
        return ServiceFactory.create("scheduler", timezone)


class MessageSenderFactory:
    """消息发送器工厂 (兼容)"""

    @staticmethod
    def create(plugin: Any) -> MessageSenderProtocol | None:
        return ServiceFactory.create("message_sender", plugin)


class ConfigProviderFactory:
    """配置提供者工厂 (兼容)"""

    @staticmethod
    def create(
        context: Any, plugin_config: dict[str, Any] | None = None
    ) -> ConfigProviderProtocol:
        return ServiceFactory.create("config_provider", context, plugin_config)


class ProactiveServicesFactory:
    """主动对话服务工厂 - 整合所有服务"""

    @staticmethod
    def create(
        context: Any,
        data_dir: Path,
        plugin_config: dict[str, Any] | None = None,
        timezone: str = "UTC",
        plugin: Any = None,
    ) -> tuple[ProactiveServices, dict[str, Any]]:
        # 创建配置提供者
        config_provider = ConfigProviderFactory.create(context, plugin_config)
        llm_settings = config_provider.llm_settings

        # 创建各个服务
        storage = StorageFactory.create(data_dir)
        scheduler = SchedulerFactory.create(timezone)

        # 合并配置 - 扁平化结构，确保顶层字段正确传递
        # llm_settings 包含 use_astrbot_provider, selected_provider, use_minimax_for_response 等
        factory_config = {"minimax_settings": llm_settings.get("minimax_settings", {})}
        # 将其他顶层字段直接添加到 factory_config
        factory_config["use_astrbot_provider"] = llm_settings.get("use_astrbot_provider", "")
        factory_config["selected_provider"] = llm_settings.get("selected_provider", "")
        factory_config["use_minimax_for_response"] = llm_settings.get("use_minimax_for_response", False)
        factory_config["debug_mode"] = llm_settings.get("debug_mode", False)
        if plugin_config:
            factory_config.update(plugin_config)

        llm = LLMFactory.create(context, factory_config)
        message_sender = MessageSenderFactory.create(plugin) if plugin else None

        # 组装服务容器
        services = ProactiveServices(
            storage=storage,
            scheduler=scheduler,
            llm=llm,
            context=context,
            config_provider=config_provider,
            message_sender=message_sender,
        )

        components = {
            "storage": storage,
            "scheduler": scheduler,
            "llm": llm,
            "config_provider": config_provider,
            "message_sender": message_sender,
        }

        return services, components


class ServiceRegistry:
    """服务注册表 - 支持服务替换"""

    def __init__(self) -> None:
        self._factories: dict[str, Any] = {}
        self._services: dict[str, Any] = {}
        self._register_default_factories()

    def _register_default_factories(self) -> None:
        """注册默认工厂"""
        self.register_factory("llm", LLMFactory.create)
        self.register_factory(
            "storage", lambda ctx, cfg, data_dir: StorageFactory.create(data_dir)
        )
        self.register_factory(
            "scheduler",
            lambda ctx, cfg, data_dir, tz=None: SchedulerFactory.create(tz or "UTC"),
        )
        self.register_factory(
            "message_sender",
            lambda ctx, cfg, data_dir, plugin: MessageSenderFactory.create(plugin),
        )
        self.register_factory("config_provider", ConfigProviderFactory.create)

    def register_factory(self, name: str, factory: Any) -> None:
        """注册工厂"""
        self._factories[name] = factory

    def register_service(self, name: str, service: Any) -> None:
        """注册服务实例"""
        self._services[name] = service

    def get_service(self, name: str) -> Any:
        """获取服务"""
        return self._services.get(name)

    def create_services(
        self,
        context: Any,
        data_dir: Path,
        plugin_config: dict | None = None,
        plugin: Any = None,
    ) -> tuple[ProactiveServices, dict]:
        """创建所有服务"""
        timezone = context.get_config().get("timezone", "UTC")
        return ProactiveServicesFactory.create(
            context=context,
            data_dir=data_dir,
            plugin_config=plugin_config,
            timezone=timezone,
            plugin=plugin,
        )


# 全局注册表
_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    """获取全局服务注册表"""
    return _registry


def create_services(
    context: Any, data_dir: Path, plugin_config: dict | None = None, plugin: Any = None
) -> tuple[ProactiveServices, dict]:
    """便捷函数：创建所有服务"""
    return get_registry().create_services(context, data_dir, plugin_config, plugin)


__all__ = [
    "StorageProtocol",
    "SchedulerProtocol",
    "LLMProtocol",
    "MessageSenderProtocol",
    "ContextProtocol",
    "ConfigProviderProtocol",
    "ProactiveServices",
    "LLMFactory",
    "StorageFactory",
    "SchedulerFactory",
    "MessageSenderFactory",
    "ConfigProviderFactory",
    "ProactiveServicesFactory",
    "ServiceRegistry",
    "get_registry",
    "create_services",
]
