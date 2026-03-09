"""
MiniMax 主动对话插件

使用 MiniMax API 进行主动对话的 AstrBot 插件。
支持私聊和群聊场景的定时/沉默/自动触发，并提供提醒功能。
支持用 LLM 替换默认对话，以及读空气判断是否回复。

作者: uuutt2023
"""

import time

import astrbot.api.star as star
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .business.config_manager import ConfigManager
from .core import ProactiveCore
from .handlers.llm_interceptor import LLMInterceptor
from .handlers.reminder import ReminderManager
from .handlers.scheduler_manager import SchedulerManager
from .services import create_services
from .utils import (
    extract_event_param,
    feature_enabled,
    format_help_message,
    format_session_status,
    with_reminder,
)


class MiniMaxProactiveChatPlugin(Star):
    """MiniMax 主动对话插件

    支持以下功能：
    - LLM 集成（支持 AstrBot 内置 Provider 或 MiniMax API）
    - 私聊/群聊主动对话
    - 定时触发、沉默触发、自动触发
    - TTS语音合成
    - 文转图功能
    """

    def __init__(self, context: Context, config: AstrBotConfig | None = None) -> None:
        super().__init__(context)
        self._start_time = time.time()

        # 初始化路径
        from pathlib import Path
        try:
            data_path = get_astrbot_data_path()
            self.data_dir = (Path(data_path) if isinstance(data_path, str) else data_path) / "plugin_data" / self.name
        except (AttributeError, TypeError):
            self.data_dir = star.StarTools.get_data_dir("astrbot_plugin_minimax_proactive")

        # 初始化配置管理器
        self._config_mgr = ConfigManager(config or self.context.get_config().get("minimax_proactive", {}) or {})

        # 创建服务
        self._services, self._components = create_services(
            context=self.context,
            data_dir=self.data_dir,
            plugin_config=self._config_mgr._config,
            plugin=self,
        )

        # 便捷访问
        self._storage = self._components["storage"]
        self._scheduler = self._components["scheduler"]
        self._llm = self._components["llm"]
        self._sender = self._components.get("message_sender")

        # 核心逻辑
        self._core = ProactiveCore(self._services)

        # 提醒管理器
        self._reminder_mgr = ReminderManager(self, self._scheduler)

        # LLM 拦截器
        self._llm_interceptor = LLMInterceptor(self._llm, self._sender, self._core)

        # 调度管理器
        self._scheduler_mgr = SchedulerManager(
            self._config_mgr, self._storage, self._scheduler, self._core, self._start_time
        )

        logger.info("[MiniMaxProactive] 插件已创建")

    # ==================== 生命周期 ====================

    async def initialize(self) -> None:
        """初始化插件"""
        await self._storage.load()
        self._scheduler.set_timezone(self.context.get_config().get("timezone", "UTC"))

        if not self._llm.is_configured:
            logger.warning("[MiniMaxProactive] 请配置 MiniMax API Key 或启用 AstrBot 内置 LLM")

        self._scheduler.start()
        await self._scheduler_mgr.restore_jobs()
        await self._scheduler_mgr.setup_auto_triggers()
        logger.info("[MiniMaxProactive] 初始化完成")

    async def terminate(self) -> None:
        """终止插件"""
        self._scheduler.shutdown()
        await self._storage.save()
        logger.info("[MiniMaxProactive] 已终止")

    # ==================== 功能开关 ====================

    def _is_proactive_chat_enabled(self) -> bool:
        return self._config_mgr.proactive_chat_enabled

    def _is_reminder_enabled(self) -> bool:
        return self._config_mgr.reminder_enabled

    # ==================== LLM 工具 ====================

    @filter.llm_tool(name="set_reminder")
    @with_reminder(restore=True)
    async def set_reminder(self, event: AstrMessageEvent, text: str, datetime_str: str, repeat: str = "none", **kwargs) -> str:
        return await self._reminder_mgr.set_reminder(event, text, datetime_str, repeat)

    @filter.llm_tool(name="delete_reminder")
    @with_reminder()
    async def delete_reminder(self, event: AstrMessageEvent, content: str = "", all: str = "no", **kwargs) -> str:
        return await self._reminder_mgr.delete_reminder(event, content, all)

    @filter.llm_tool(name="list_reminders")
    @with_reminder()
    async def list_reminders(self, event: AstrMessageEvent, **kwargs) -> str:
        return await self._reminder_mgr.list_reminders(event)

    # ==================== 指令系统 ====================

    @filter.command_group("mpro")
    def mpro_cmd(self):
        """MiniMax主动对话指令"""
        pass

    @mpro_cmd.command("help")
    async def cmd_help(self, event: AstrMessageEvent) -> str:
        return format_help_message()

    @mpro_cmd.command("status")
    async def cmd_status(self, event: AstrMessageEvent) -> str:
        return format_session_status(self._is_proactive_chat_enabled(), self._is_reminder_enabled())

    @mpro_cmd.command("add")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    @with_reminder(restore=True)
    async def cmd_add(self, event: AstrMessageEvent, time_str: str, *args, **kwargs) -> str:
        text = " ".join(args)
        if not text:
            return "请输入提醒内容"
        return await self._reminder_mgr.set_reminder(event, text, time_str, "none")

    @mpro_cmd.command("ls")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    @with_reminder()
    async def cmd_list(self, event: AstrMessageEvent, **kwargs) -> str:
        return await self._reminder_mgr.list_reminders(event)

    @mpro_cmd.command("rm")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    @with_reminder()
    async def cmd_rm(self, event: AstrMessageEvent, index: int, **kwargs) -> str:
        return await self._reminder_mgr.delete_reminder_by_index(event, index)

    @mpro_cmd.command("clear")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    @with_reminder()
    async def cmd_clear(self, event: AstrMessageEvent, **kwargs) -> str:
        return await self._reminder_mgr.delete_reminder(event, "", "yes")

    # ==================== 消息监听 ====================

    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE, priority=999)
    async def on_private(self, event: AstrMessageEvent) -> None:
        await self._core.handle_message(event)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE, priority=998)
    async def on_group(self, event: AstrMessageEvent) -> None:
        await self._core.handle_message(event)

    @filter.after_message_sent()
    async def after_sent(self, event: AstrMessageEvent) -> None:
        if "group" in event.unified_msg_origin.lower():
            await self._core.handle_after_send(event.unified_msg_origin)

    # ==================== LLM 拦截 ====================

    def _get_session_context(self, event: AstrMessageEvent) -> tuple[str, dict] | None:
        """获取会话上下文"""
        if not event:
            return None
        session_id = event.unified_msg_origin
        cfg = self._services.get_session_config(session_id)
        return (session_id, cfg) if cfg else None

    @filter.on_llm_request(priority=99)
    @extract_event_param()
    async def on_llm_request(self, event: AstrMessageEvent, request=None, **kwargs) -> None:
        if not event or not self._llm.available:
            return

        ctx = self._get_session_context(event)
        if not ctx:
            return

        session_id, cfg = ctx
        await self._llm_interceptor.handle_llm_request(event, request, session_id, cfg)

    @filter.on_llm_request(priority=50)
    @extract_event_param()
    async def read_air_and_decide(self, event: AstrMessageEvent, request=None, **kwargs) -> None:
        if not event or not self._llm.available:
            return

        ctx = self._get_session_context(event)
        if not ctx:
            return

        session_id, cfg = ctx
        await self._llm_interceptor.handle_read_air(event, request, session_id, cfg)
