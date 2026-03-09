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

from .src import ConfigManager
from .src.constants import (
    ConfigKeys,
    Defaults,
    EmojiGateKeys,
    MessageKeys,
    ProactiveKeys,
    ReadAirKeys,
    ScheduleKeys,
    StorageKeys,
)
from .src.helpers import (
    check_and_stop_request,
    extract_text_from_messages,
    has_image_in_messages,
    is_emoji_only,
)
from .core import ProactiveCore
from .services import create_services
from .src.llm import LLMCaller
from .src.messager import MessageSender
from .src.reminder import ReminderManager
from .libs import (
    format_help_message,
    format_session_status,
    feature_enabled,
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

        # 初始化路径 - 使用 AstrBot 推荐的 plugin_data 目录
        # v4.9.2+ 使用 get_astrbot_data_path()，兼容旧版本使用 star.StarTools.get_data_dir()
        from pathlib import Path
        try:
            # v4.9.2+ 推荐方式
            data_path = get_astrbot_data_path()
            # 确保返回的是 Path 对象
            if isinstance(data_path, str):
                data_path = Path(data_path)
            self.data_dir = data_path / "plugin_data" / self.name
        except (AttributeError, TypeError):
            # 兼容旧版本
            self.data_dir = star.StarTools.get_data_dir("astrbot_plugin_minimax_proactive")

        # 初始化配置管理器（用于获取配置）
        if config:
            self._config_mgr = ConfigManager(config)
        else:
            plugin_config = self.context.get_config().get("minimax_proactive", {}) or {}
            self._config_mgr = ConfigManager(plugin_config)

        # 使用工厂创建服务 - 传递完整配置（包括debug_mode和所有配置）
        self._services, self._components = create_services(
            context=self.context,
            data_dir=self.data_dir,
            plugin_config=self._config_mgr._config,  # 传递完整配置
            plugin=self,  # 传入 self 用于创建消息发送器
        )

        # 便捷访问
        self._storage = self._components["storage"]
        self._scheduler = self._components["scheduler"]
        self._llm: LLMCaller = self._components["llm"]
        self._sender: MessageSender | None = self._components["message_sender"]

        # 核心逻辑 - 使用依赖注入
        self._core = ProactiveCore(self._services)

        # 提醒管理器
        self._reminder_mgr = ReminderManager(self, self._scheduler)

        logger.info("[MiniMaxProactive] [INFO] [__init__] 插件已创建")

    # ==================== 生命周期 ====================

    async def initialize(self) -> None:
        """初始化插件"""
        await self._storage.load()

        # 设置时区
        tz = self.context.get_config().get("timezone", "UTC")
        self._scheduler.set_timezone(tz)

        # 检查API配置
        if not self._llm.is_configured:
            logger.warning(
                "[MiniMaxProactive] [WARNING] [initialize] 请配置 MiniMax API Key 或启用 AstrBot 内置 LLM"
            )

        # 启动调度器并恢复任务
        self._scheduler.start()
        await self._restore_jobs()
        await self._setup_auto_triggers()

        logger.info("[MiniMaxProactive] 初始化完成")

    async def terminate(self) -> None:
        """终止插件"""
        self._scheduler.shutdown()
        await self._storage.save()
        logger.info("[MiniMaxProactive] 已终止")

    # ==================== 功能开关检查 ====================

    def _is_proactive_chat_enabled(self) -> bool:
        return self._config_mgr.proactive_chat_enabled

    def _is_reminder_enabled(self) -> bool:
        return self._config_mgr.reminder_enabled

    # ==================== LLM 工具 ====================

    @filter.llm_tool(name="set_reminder")
    async def set_reminder(
        self,
        event: AstrMessageEvent,
        text: str,
        datetime_str: str,
        repeat: str = "none",
    ) -> str:
        """设置一个提醒"""
        if not self._is_reminder_enabled():
            return "提醒功能已关闭"
        await self._reminder_mgr.load()
        result = await self._reminder_mgr.set_reminder(
            event, text, datetime_str, repeat
        )
        await self._reminder_mgr.restore_jobs()
        return result

    @filter.llm_tool(name="delete_reminder")
    async def delete_reminder(
        self,
        event: AstrMessageEvent,
        content: str = "",
        all: str = "no",
    ) -> str:
        """删除提醒"""
        if not self._is_reminder_enabled():
            return "提醒功能已关闭"
        await self._reminder_mgr.load()
        return await self._reminder_mgr.delete_reminder(event, content, all)

    @filter.llm_tool(name="list_reminders")
    async def list_reminders(self, event: AstrMessageEvent) -> str:
        """列出当前所有提醒"""
        if not self._is_reminder_enabled():
            return "提醒功能已关闭"
        await self._reminder_mgr.load()
        return await self._reminder_mgr.list_reminders(event)

    # ==================== 指令系统 ====================

    @filter.command_group("mpro")
    def mpro_cmd(self):
        """MiniMax主动对话指令"""
        pass

    @mpro_cmd.command("help")
    async def cmd_help(self, event: AstrMessageEvent) -> str:
        """显示帮助信息"""
        return format_help_message()

    @mpro_cmd.command("status")
    async def cmd_status(self, event: AstrMessageEvent) -> str:
        """查看功能状态"""
        return format_session_status(
            self._is_proactive_chat_enabled(),
            self._is_reminder_enabled()
        )

    @mpro_cmd.command("add")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    async def cmd_add(self, event: AstrMessageEvent, time_str: str, *args) -> str:
        """添加提醒"""
        text = " ".join(args)
        if not text:
            return "请输入提醒内容"
        await self._reminder_mgr.load()
        result = await self._reminder_mgr.set_reminder(event, text, time_str, "none")
        await self._reminder_mgr.restore_jobs()
        return result

    @mpro_cmd.command("ls")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    async def cmd_list(self, event: AstrMessageEvent) -> str:
        """列出提醒"""
        await self._reminder_mgr.load()
        return await self._reminder_mgr.list_reminders(event)

    @mpro_cmd.command("rm")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    async def cmd_rm(self, event: AstrMessageEvent, index: int) -> str:
        """删除提醒"""
        await self._reminder_mgr.load()
        return await self._reminder_mgr.delete_reminder_by_index(event, index)

    @mpro_cmd.command("clear")
    @feature_enabled(lambda self: self._is_reminder_enabled())
    async def cmd_clear(self, event: AstrMessageEvent) -> str:
        """删除所有提醒"""
        await self._reminder_mgr.load()
        return await self._reminder_mgr.delete_reminder(event, "", "yes")

    # ==================== 消息监听 ====================

    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE, priority=999)
    async def on_private(self, event: AstrMessageEvent, *args, **kwargs) -> None:
        """私聊消息处理"""
        if event and isinstance(event, AstrMessageEvent):
            await self._core.handle_message(event)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE, priority=998)
    async def on_group(self, event: AstrMessageEvent, *args, **kwargs) -> None:
        """群聊消息处理"""
        if event and isinstance(event, AstrMessageEvent):
            await self._core.handle_message(event)

    @filter.after_message_sent()
    async def after_sent(self, event: AstrMessageEvent, *args, **kwargs) -> None:
        """消息发送后处理"""
        if event and isinstance(event, AstrMessageEvent) and "group" in event.unified_msg_origin.lower():
            await self._core.handle_after_send(event.unified_msg_origin)

    # ==================== 调度管理 ====================

    async def _restore_jobs(self) -> None:
        """恢复定时任务"""
        now = time.time()
        count = 0

        for session_id, data in self._storage.data.items():
            cfg = self._config_mgr.get_session_config(session_id)
            if not cfg:
                continue

            next_time = data.get(StorageKeys.NEXT_TRIGGER_TIME, 0)
            if next_time and next_time > now:
                delay = int(next_time - now)
                schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
                min_i = (
                    int(
                        schedule.get(
                            ScheduleKeys.MIN_INTERVAL_MINUTES,
                            Defaults.MIN_INTERVAL_MINUTES,
                        )
                    )
                    * 60
                )
                max_i = max(
                    min_i,
                    int(
                        schedule.get(
                            ScheduleKeys.MAX_INTERVAL_MINUTES,
                            Defaults.MAX_INTERVAL_MINUTES,
                        )
                    )
                    * 60,
                )
                self._scheduler.add_job(
                    self._core.check_and_chat, session_id, delay, min_i, max_i
                )
                count += 1

        logger.info(f"[MiniMaxProactive] 恢复 {count} 个任务")

    async def _setup_auto_triggers(self) -> None:
        """设置自动触发"""
        logger.info("[MiniMaxProactive] 检查自动触发...")

        # 处理单独私聊会话
        for cfg in self._config_mgr.private_sessions:
            if cfg.get(ConfigKeys.ENABLE) and cfg.get(ConfigKeys.SESSION_ID):
                await self._setup_single_auto(
                    cfg, f"default:FriendMessage:{cfg[ConfigKeys.SESSION_ID]}"
                )

        # 处理单独群聊会话
        for cfg in self._config_mgr.group_sessions:
            if cfg.get(ConfigKeys.ENABLE) and cfg.get(ConfigKeys.SESSION_ID):
                await self._setup_single_auto(
                    cfg, f"default:GroupMessage:{cfg[ConfigKeys.SESSION_ID]}"
                )

        # 处理私聊全局默认设置
        private_default = self._config_mgr.private_default_settings
        if private_default.get(ConfigKeys.ENABLE) and private_default.get(
            ScheduleKeys.AUTO_TRIGGER_SETTINGS, {}
        ).get(ScheduleKeys.ENABLE_AUTO_TRIGGER):
            logger.info("[MiniMaxProactive] 私聊全局自动触发已启用")

        # 处理群聊全局默认设置
        group_default = self._config_mgr.group_default_settings
        if group_default.get(ConfigKeys.ENABLE) and group_default.get(
            ScheduleKeys.AUTO_TRIGGER_SETTINGS, {}
        ).get(ScheduleKeys.ENABLE_AUTO_TRIGGER):
            logger.info("[MiniMaxProactive] 群聊全局自动触发已启用")

        logger.info("[MiniMaxProactive] 自动触发检查完成")

    async def _setup_single_auto(self, cfg: dict, session_id: str) -> None:
        """设置单个自动触发"""
        auto = cfg.get(ScheduleKeys.AUTO_TRIGGER_SETTINGS, {})
        if not auto.get(ScheduleKeys.ENABLE_AUTO_TRIGGER):
            return

        minutes = auto.get(
            ScheduleKeys.AUTO_TRIGGER_AFTER_MINUTES, Defaults.AUTO_TRIGGER_AFTER_MINUTES
        )
        if minutes <= 0:
            return

        # 检查是否已有消息
        if session_id not in self._core._message_times:
            elapsed = time.time() - self._start_time
            if elapsed >= minutes * 60:
                schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
                min_i = (
                    int(
                        schedule.get(
                            ScheduleKeys.MIN_INTERVAL_MINUTES,
                            Defaults.MIN_INTERVAL_MINUTES,
                        )
                    )
                    * 60
                )
                max_i = max(
                    min_i,
                    int(
                        schedule.get(
                            ScheduleKeys.MAX_INTERVAL_MINUTES,
                            Defaults.MAX_INTERVAL_MINUTES,
                        )
                    )
                    * 60,
                )
                self._scheduler.add_job(
                    self._core.check_and_chat, session_id, 0, min_i, max_i
                )

    # ==================== LLM 拦截 ====================

    @filter.on_llm_request(priority=99)
    async def on_llm_request(self, *args, **kwargs) -> None:
        """拦截LLM请求，用配置的LLM替换默认对话"""
        # 兼容不同版本的参数传递方式
        event = None
        request = None
        for arg in args:
            if isinstance(arg, AstrMessageEvent):
                event = arg
                break
        if not event:
            event = kwargs.get("event")
        request = kwargs.get("request") or (args[1] if len(args) > 1 else None)
        
        if not event or not self._llm.available:
            return

        session_id = event.unified_msg_origin
        cfg = self._services.get_session_config(session_id)

        if not cfg or not cfg.get(ProactiveKeys.USE_MINIMAX_FOR_RESPONSE, False):
            return

        # 获取用户消息
        messages = event.get_messages()
        if not messages:
            return

        user_text = ""
        for msg in messages:
            if hasattr(msg, "text"):
                user_text += msg.text
            elif hasattr(msg, "get_text"):
                user_text += msg.get_text() or ""

        if not user_text:
            return

        logger.info(f"[MiniMaxProactive] 使用LLM处理对话: {session_id}")

        try:
            ctx = await self._core._get_context(session_id)
            if not ctx:
                return

            from .libs import sanitize_history

            history = sanitize_history(ctx["history"])
            history.append({"role": "user", "content": user_text})

            response = await self._llm.chat(user_text, history, ctx["system_prompt"])
            response = response.strip()

            if response and response != "[object Object]":
                if self._sender:
                    tts = cfg.get(MessageKeys.TTS_SETTINGS, {})
                    t2i = cfg.get(MessageKeys.T2I_SETTINGS, {})
                    await self._sender.send(session_id, response, tts, t2i)

                if request is not None:
                    if hasattr(request, "stop_propagation"):
                        request.stop_propagation()
                    elif hasattr(request, "terminated"):
                        request.terminated = True

                logger.info(f"[MiniMaxProactive] LLM对话完成: {session_id}")
        except Exception as e:
            logger.error(f"[MiniMaxProactive] LLM对话失败: {e}")

    @filter.on_llm_request(priority=50)
    async def read_air_and_decide(self, *args, **kwargs) -> None:
        """读空气判断是否需要回复，包含表情包守门员功能"""
        # 兼容不同版本的参数传递方式
        event = None
        request = None
        for arg in args:
            if isinstance(arg, AstrMessageEvent):
                event = arg
                break
        if not event:
            event = kwargs.get("event")
        request = kwargs.get("request") or (args[1] if len(args) > 1 else None)

        if not event or not self._llm.available:
            return

        session_id = event.unified_msg_origin
        cfg = self._services.get_session_config(session_id)

        if not cfg:
            return

        messages = event.get_messages()
        if not messages:
            return

        # 提取用户消息文本和图片
        user_text = extract_text_from_messages(messages)
        has_image = has_image_in_messages(messages)

        # 检查是否是单独发表情包（只有图片，没有文字或只有表情符号）
        is_emoji_only_msg = has_image and (not user_text.strip() or is_emoji_only(user_text))

        # 表情包守门员逻辑
        if is_emoji_only_msg:
            emoji_gate_enabled = cfg.get(EmojiGateKeys.EMOJI_GATE_ENABLED, False)
            if emoji_gate_enabled:
                import random
                emoji_rate = cfg.get(EmojiGateKeys.EMOJI_GATE_RATE, Defaults.EMOJI_GATE_RATE)
                if random.randint(1, 100) > emoji_rate:
                    # 概率不放行，阻止回复
                    if request is not None:
                        check_and_stop_request(request)
                    logger.info(f"[MiniMaxProactive] 表情包守门员阻止回复: {session_id}")
                    return
                else:
                    # 概率放行，继续执行
                    logger.info(f"[MiniMaxProactive] 表情包守门员放行: {session_id}")

        # 原有读空气逻辑
        read_air_cfg = cfg.get(ReadAirKeys.READ_AIR_SETTINGS, {})
        if not read_air_cfg.get(ReadAirKeys.ENABLE_READ_AIR, False):
            return

        if not user_text:
            return

        logger.info(f"[MiniMaxProactive] 读空气判断: {session_id}")

        try:
            # 优先使用配置，其次使用 prompts 模块
            from .prompts import DEFAULT_READ_AIR

            system_prompt = read_air_cfg.get(
                ReadAirKeys.READ_AIR_PROMPT, DEFAULT_READ_AIR
            )

            history = [
                {"role": "user", "content": f"请判断以下消息是否需要回复：{user_text}"}
            ]
            result = await self._llm.chat("", history, system_prompt)
            result = result.strip().upper()

            should_respond = "YES" in result or "应该" in result or "需要" in result

            if not should_respond:
                if request is not None:
                    check_and_stop_request(request)
                logger.info(f"[MiniMaxProactive] 读空气判断不需要回复: {session_id}")
            else:
                logger.info(f"[MiniMaxProactive] 读空气判断需要回复: {session_id}")

        except Exception as e:
            logger.error(f"[MiniMaxProactive] 读空气判断失败: {e}")
