"""
核心逻辑模块

包含主动对话的核心业务逻辑。
使用依赖注入解耦。
支持高并发访问。

重构后使用多个专业化组件:
- StateManager: 并发安全的状态管理
- ContextProvider: 对话上下文获取
- ProactiveScheduler: 触发调度逻辑

作者: uuutt2023
"""


from astrbot.api import logger

from ..business.constants import (
    MessageKeys,
)
from ..services import ProactiveServices
from ..utils import format_log, sanitize_history
from ..utils.decorators import log, timed
from .context_provider import ContextProvider
from .proactive_scheduler import ProactiveScheduler
from .state_manager import StateManager


class ProactiveCore:
    """主动对话核心逻辑 - 使用依赖注入和组件化

    支持高并发访问。
    内部组件化重构，降低耦合。
    """

    def __init__(self, services: ProactiveServices) -> None:
        self._services = services

        # 初始化组件
        self._state_mgr = StateManager(services.storage)
        self._context_provider = ContextProvider(
            services.context,
            services.llm,
            services.storage,
        )
        self._proactive_scheduler = ProactiveScheduler(
            services.scheduler,
            services.storage,
            services.scheduler.timezone,
        )

    @log("处理收到消息")
    async def handle_message(self, event) -> None:
        """处理接收到的消息"""
        messages = event.get_messages()
        if not messages:
            return

        session_id = event.unified_msg_origin
        cfg = self._services.get_session_config(session_id)
        if not cfg:
            return

        # 记录消息
        await self._state_mgr.record_message(session_id)

        # 记录日志（每会话一次）
        if await self._state_mgr.should_log(session_id):
            logger.info(f"[MiniMaxProactive] 收到消息: {format_log(session_id, cfg)}")

        # 调度下次触发
        await self._schedule_trigger(session_id, cfg)

    async def handle_after_send(self, session_id: str) -> None:
        """消息发送后处理"""
        cfg = self._services.get_session_config(session_id)
        if not cfg:
            return

        # 使用调度器安排沉默触发
        self._proactive_scheduler.schedule_idle_trigger(
            session_id, cfg, self._on_idle
        )

    async def _on_idle(self, session_id: str) -> None:
        """群聊沉默触发"""
        cfg = self._services.get_session_config(session_id)
        if not cfg:
            return

        count = await self._state_mgr.get_unanswered_count(session_id)
        logger.info(f"[MiniMaxProactive] 群聊沉默触发 (未回复: {count})")
        await self._schedule_trigger(session_id, cfg)

    @log("执行主动聊天任务")
    @timed()
    async def check_and_chat(self, session_id: str) -> None:
        """主动聊天任务"""
        cfg = self._services.get_session_config(session_id)
        if not cfg:
            return

        # 检查免打扰时段
        if self._proactive_scheduler.is_quiet_time(cfg):
            await self._schedule_trigger(session_id, cfg)
            return

        # 检查触发上限
        count = await self._state_mgr.get_unanswered_count(session_id)
        if self._proactive_scheduler.reached_limit(cfg, count):
            return

        logger.info(f"[MiniMaxProactive] 开始第 {count + 1} 次主动消息")

        # 获取上下文
        ctx = await self._context_provider.get_context(session_id)
        if not ctx:
            await self._schedule_trigger(session_id, cfg)
            return

        # 处理图片描述
        cfg = self._services.get_session_config(session_id)
        if cfg:
            image_desc_cfg = cfg.get("image_desc_settings", {})
            if image_desc_cfg.get("enable_image_desc"):
                ctx["history"] = await self._context_provider.process_image_descriptions(
                    ctx["history"],
                    session_id,
                    image_desc_cfg,
                )

        # 发送消息（cfg 已在前面检查过非空）
        if cfg:
            await self._send_proactive_message(session_id, cfg, ctx, count)

    async def _send_proactive_message(
        self, session_id: str, cfg: dict, ctx: dict, count: int
    ) -> None:
        """发送主动消息"""
        try:
            # 使用调度器构建Prompt
            from ..prompts import DEFAULT_GROUP_PROACTIVE, DEFAULT_PRIVATE_PROACTIVE
            prompt = self._proactive_scheduler.build_prompt(
                cfg,
                count,
                DEFAULT_PRIVATE_PROACTIVE,
                DEFAULT_GROUP_PROACTIVE,
            )

            # 调用LLM
            history = sanitize_history(ctx["history"])
            response = await self._services.llm.chat(
                prompt, history, ctx["system_prompt"]
            )
            response = response.strip()

            if response == "[object Object]":
                await self._schedule_trigger(session_id, cfg)
                return

            # 发送消息
            sender = self._services.message_sender
            if sender:
                tts = cfg.get(MessageKeys.TTS_SETTINGS, {})
                t2i = cfg.get(MessageKeys.T2I_SETTINGS, {})
                await sender.send(session_id, response, tts, t2i)

            # 更新计数
            await self._state_mgr.increment_unanswered(session_id)

            # 调度下次
            await self._schedule_trigger(session_id, cfg)

        except Exception as e:
            logger.error(f"[MiniMaxProactive] LLM调用失败: {e}")
            await self._schedule_trigger(session_id, cfg)

    async def _schedule_trigger(self, session_id: str, cfg: dict) -> None:
        """调度下次触发"""
        self._proactive_scheduler.schedule_trigger(
            session_id,
            cfg,
            self.check_and_chat,
        )
