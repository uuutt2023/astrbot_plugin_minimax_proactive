"""
核心逻辑模块

包含主动对话的核心业务逻辑。
使用依赖注入解耦。
支持高并发访问。

作者: uuutt2023
"""

import asyncio
import orjson
import random
import time
from datetime import datetime
from typing import Any

from astrbot.api import logger

from ..src.constants import (
    ConfigKeys,
    Defaults,
    MessageKeys,
    ProactiveKeys,
    ScheduleKeys,
    StorageKeys,
)
from ..src.decorators import error_handler, log, timed
from ..services import ProactiveServices
from ..prompts import DEFAULT_PRIVATE_PROACTIVE, DEFAULT_GROUP_PROACTIVE, DEFAULT_IMAGE_DESC
from ..libs import format_log, sanitize_history, replace_image_with_text, is_quiet_time


# 图片描述缓存 - 避免重复调用 LLM
_IMAGE_CAPTION_CACHE: dict[str, str] = {}


class ProactiveCore:
    """主动对话核心逻辑 - 使用依赖注入

    支持高并发访问。
    """

    def __init__(self, services: ProactiveServices) -> None:
        self._services = services
        self._message_times: dict[str, float] = {}
        self._logged: set[str] = set()
        self._lock = asyncio.Lock()  # 异步锁
        # 图片描述超时时间（秒）
        self._image_caption_timeout = 30

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

        now = time.time()
        self._message_times[session_id] = now

        # 保存状态
        storage = self._services.storage
        data = storage.get_sync(session_id, {})
        if (
            data.get(StorageKeys.LAST_TIME, 0) == 0
            or data.get(StorageKeys.UNANSWERED_COUNT, 0) != 0
        ):
            storage.set_sync(
                session_id,
                {StorageKeys.LAST_TIME: now, StorageKeys.UNANSWERED_COUNT: 0},
            )
            await storage.save()

            # 日志
        if session_id not in self._logged:
            self._logged.add(session_id)
            from ..libs import format_log

            logger.info(f"[MiniMaxProactive] 收到消息: {format_log(session_id, cfg)}")

        # 调度下次触发
        await self._schedule_trigger(session_id, cfg)

    async def handle_after_send(self, session_id: str) -> None:
        """消息发送后处理"""
        cfg = self._services.get_session_config(session_id)
        if not cfg:
            return

        idle_minutes = cfg.get(
            ProactiveKeys.GROUP_IDLE_TRIGGER_MINUTES,
            Defaults.GROUP_IDLE_TRIGGER_MINUTES,
        )
        self._services.scheduler.add_job(self._on_idle, session_id, idle_minutes * 60)

    async def _on_idle(self, session_id: str) -> None:
        """群聊沉默触发"""
        cfg = self._services.get_session_config(session_id)
        if not cfg:
            return

        count = self._get_unanswered_count(session_id)
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
        if self._is_quiet_time(cfg):
            await self._schedule_trigger(session_id, cfg)
            return

        # 检查触发上限
        count = self._get_unanswered_count(session_id)
        if self._reached_limit(cfg, count):
            return

        logger.info(f"[MiniMaxProactive] 开始第 {count + 1} 次主动消息")

        # 获取上下文
        ctx = await self._get_context(session_id)
        if not ctx:
            await self._schedule_trigger(session_id, cfg)
            return

        # 发送消息
        await self._send_proactive_message(session_id, cfg, ctx, count)

    async def _send_proactive_message(
        self, session_id: str, cfg: dict, ctx: dict, count: int
    ) -> None:
        """发送主动消息"""
        try:
            # 构建Prompt - 优先使用配置，其次使用 prompts 模块
            from ..prompts import DEFAULT_PRIVATE_PROACTIVE, DEFAULT_GROUP_PROACTIVE

            prompt = cfg.get(ProactiveKeys.PROACTIVE_PROMPT, "")
            if not prompt:
                # 根据会话类型选择默认 Prompt
                session_type = cfg.get(ConfigKeys.SESSION_TYPE, "private")
                if session_type == "group":
                    prompt = DEFAULT_GROUP_PROACTIVE
                else:
                    prompt = DEFAULT_PRIVATE_PROACTIVE
            now_str = datetime.now(self._services.scheduler.timezone).strftime(
                "%Y年%m月%d日 %H:%M"
            )
            prompt = prompt.replace("{{unanswered_count}}", str(count)).replace(
                "{{current_time}}", now_str
            )

            # 调用LLM
            from ..libs import sanitize_history

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
            storage = self._services.storage
            data = storage.get_sync(session_id, {})
            data[StorageKeys.UNANSWERED_COUNT] = count + 1
            storage.set_sync(session_id, data)

            # 调度下次
            await self._schedule_trigger(session_id, cfg)

        except Exception as e:
            logger.error(f"[MiniMaxProactive] LLM调用失败: {e}")
            await self._schedule_trigger(session_id, cfg)

    @error_handler(default_return=None, log_error=True)
    async def _get_context(self, session_id: str) -> dict | None:
        """获取对话上下文"""
        try:
            ctx = self._services.context
            conv_mgr = getattr(ctx, "conversation_manager", None)
            if not conv_mgr:
                return None

            conv_id = await conv_mgr.get_curr_conversation_id(session_id)
            if not conv_id:
                conv_id = await conv_mgr.new_conversation(session_id)
            if not conv_id:
                return None

            conv = await conv_mgr.get_conversation(session_id, conv_id)

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

            # 处理表情包转述
            cfg = self._services.get_session_config(session_id)
            if cfg:
                image_desc_cfg = cfg.get("image_desc_settings", {})
                if image_desc_cfg.get("enable_image_desc"):
                    history = await self._process_image_descriptions(
                        history, 
                        image_desc_cfg,
                        session_id
                    )

            prompt = ""
            persona_mgr = getattr(ctx, "persona_manager", None)

            if conv and conv.persona_id and persona_mgr:
                persona = await persona_mgr.get_persona(conv.persona_id)
                if persona:
                    prompt = persona.system_prompt

            if not prompt and persona_mgr:
                default = await persona_mgr.get_default_persona_v3(umo=session_id)
                if default:
                    prompt = default.get("prompt", "")

            if not prompt:
                logger.error("[MiniMaxProactive] 无法加载人格设定")
                return None

            return {"conv_id": conv_id, "history": history, "system_prompt": prompt}
        except Exception as e:
            logger.warning(f"[MiniMaxProactive] 获取上下文失败: {e}")
            return None

    async def _process_image_descriptions(
        self, 
        history: list, 
        image_desc_cfg: dict,
        session_id: str
    ) -> list:
        """处理历史消息中的表情包转述
        
        Args:
            history: 历史消息列表
            image_desc_cfg: 表情包转述配置
            session_id: 会话ID
            
        Returns:
            处理后的历史消息列表
        """
        global _IMAGE_CAPTION_CACHE
        
        from astrbot.api import logger
        from ..libs import replace_image_with_text
        from ..prompts import DEFAULT_IMAGE_DESC
        
        # 获取提示词
        image_desc_prompt = image_desc_cfg.get("image_desc_prompt") or DEFAULT_IMAGE_DESC
        
        # 获取 LLM
        llm = self._services.llm
        
        # 获取超时设置
        timeout = image_desc_cfg.get("image_desc_timeout", self._image_caption_timeout)
        
        processed_history = []
        
        for msg in history:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                
                # 检查是否包含表情包标记
                if "[表情]" in content or "[图片]" in content:
                    # 尝试获取图片URL - 支持多种字段名
                    image_url = msg.get("image_url") or msg.get("image") or msg.get("url")
                    
                    if image_url:
                        description = None
                        
                        # 检查缓存
                        if image_url in _IMAGE_CAPTION_CACHE:
                            description = _IMAGE_CAPTION_CACHE[image_url]
                            logger.info(f"[MiniMaxProactive] 命中图片描述缓存: {image_url[:30]}...")
                        else:
                            # 调用 LLM 描述图片（带超时控制）
                            logger.info("[MiniMaxProactive] 正在描述图片...")
                            try:
                                description = await asyncio.wait_for(
                                    llm.describe_image(
                                        image_url=image_url,
                                        prompt=image_desc_prompt,
                                        session_id=session_id
                                    ),
                                    timeout=timeout
                                )
                                
                                # 缓存结果
                                if description:
                                    _IMAGE_CAPTION_CACHE[image_url] = description
                                    logger.info(f"[MiniMaxProactive] 缓存图片描述: {image_url[:30]}...")
                            except asyncio.TimeoutError:
                                logger.warning(f"[MiniMaxProactive] 图片转述超时，超过 {timeout} 秒")
                            except Exception as e:
                                logger.error(f"[MiniMaxProactive] 图片转述失败: {e}")
                        
                        if description:
                            # 替换表情包标记为转述文本
                            content = replace_image_with_text(content, description.strip())
                            logger.info(f"[MiniMaxProactive] 图片转述: {description[:50]}...")
                        else:
                            # 转述失败，替换为占位符
                            content = replace_image_with_text(content, "图片")
                    
                    msg["content"] = content
            
            processed_history.append(msg)
        
        return processed_history

    def _is_quiet_time(self, cfg: dict) -> bool:
        """检查是否在免打扰时段"""
        from ..libs import is_quiet_time

        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        return is_quiet_time(
            schedule.get(ScheduleKeys.QUIET_HOURS, Defaults.QUIET_HOURS),
            self._services.scheduler.timezone,
        )

    def _reached_limit(self, cfg: dict, count: int) -> bool:
        """检查是否达到触发上限"""
        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        max_count = schedule.get(
            ScheduleKeys.MAX_UNANSWERED_TIMES, Defaults.MAX_UNANSWERED_TIMES
        )
        if max_count > 0 and count >= max_count:
            logger.info(f"[MiniMaxProactive] 达到上限 ({count}/{max_count})")
            return True
        return False

    # ========== 内部方法 ==========

    def _get_unanswered_count(self, session_id: str) -> int:
        """获取未回复计数"""
        return self._services.storage.get_sync(session_id, {}).get(
            StorageKeys.UNANSWERED_COUNT, 0
        )

    async def _schedule_trigger(self, session_id: str, cfg: dict) -> None:
        """调度下次触发"""
        schedule = cfg.get(ScheduleKeys.SCHEDULE_SETTINGS, {})
        min_i = (
            int(
                schedule.get(
                    ScheduleKeys.MIN_INTERVAL_MINUTES, Defaults.MIN_INTERVAL_MINUTES
                )
            )
            * 60
        )
        max_i = max(
            min_i,
            int(
                schedule.get(
                    ScheduleKeys.MAX_INTERVAL_MINUTES, Defaults.MAX_INTERVAL_MINUTES
                )
            )
            * 60,
        )

        # 添加随机延迟
        delay = random.randint(min_i, max_i)

        self._services.scheduler.add_job(
            self.check_and_chat, session_id, 0, min_i, max_i
        )

        # 保存下次触发时间
        storage = self._services.storage
        data = storage.get_sync(session_id, {})
        data[StorageKeys.NEXT_TRIGGER_TIME] = time.time() + delay
        storage.set_sync(session_id, data)
