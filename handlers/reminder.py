"""
提醒功能模块

该模块提供提醒功能集成，支持通过LLM设置/删除/查看提醒。
使用 AstrBot 官方 KV 存储 API。

作者: uuutt2023
"""

from __future__ import annotations

import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import JobLookupError

from astrbot.api import logger


class ReminderManager:
    """提醒管理器

    使用 APScheduler 管理定时提醒任务。
    使用 AstrBot 官方 KV 存储。
    """

    def __init__(self, plugin: Any, scheduler: AsyncIOScheduler) -> None:
        self.plugin: Any = plugin
        self.scheduler: AsyncIOScheduler = scheduler

    async def load(self) -> dict[str, Any]:
        """加载提醒数据 - 使用官方 KV 存储"""
        data = await self.plugin.get_kv_data("reminders", {})
        return data if data else {}

    async def save(self, data: dict[str, Any]) -> None:
        """保存提醒数据 - 使用官方 KV 存储"""
        await self.plugin.put_kv_data("reminders", data)

    def _get_session_key(self, event: Any) -> str:
        """获取会话键"""
        if hasattr(event, "unified_msg_origin"):
            return event.unified_msg_origin
        return "default"

    async def set_reminder(
        self,
        event: Any,
        text: str,
        datetime_str: str,
        repeat: str | None = None,
    ) -> str:
        """设置提醒"""
        try:
            session_key = self._get_session_key(event)
            creator_id = getattr(event, "get_sender_id", lambda: None)()

            # 加载数据
            reminder_data = await self.load()
            if session_key not in reminder_data:
                reminder_data[session_key] = []

            # 解析时间
            dt = self._parse_datetime(datetime_str)
            if not dt:
                return f"时间格式错误: {datetime_str}，请使用 YYYY-MM-DD HH:MM 格式"

            # 创建提醒
            reminder = {
                "text": text,
                "datetime": dt.strftime("%Y-%m-%d %H:%M"),
                "repeat": repeat or "none",
                "creator_id": creator_id,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

            reminder_data[session_key].append(reminder)

            # 添加调度任务
            job_id = self._add_scheduler_job(session_key, reminder, dt)
            reminder["job_id"] = job_id

            await self.save(reminder_data)

            repeat_str = ""
            if repeat == "daily":
                repeat_str = "，每天重复"
            elif repeat == "weekly":
                repeat_str = "，每周重复"
            elif repeat == "monthly":
                repeat_str = "，每月重复"
            elif repeat == "yearly":
                repeat_str = "，每年重复"

            return (
                f"已设置提醒：{text}\n时间：{dt.strftime('%Y-%m-%d %H:%M')}{repeat_str}"
            )

        except Exception as e:
            logger.error(f"设置提醒失败: {e}")
            return f"设置提醒失败: {str(e)}"

    async def delete_reminder(
        self, event: Any, content: str | None = None, all: str = "no"
    ) -> str:
        """删除提醒"""
        try:
            session_key = self._get_session_key(event)
            reminder_data = await self.load()

            if session_key not in reminder_data:
                return "当前没有任何提醒"

            reminders = reminder_data[session_key]

            if not reminders:
                return "当前没有任何提醒"

            if all.lower() == "yes":
                count = len(reminders)
                for r in reminders:
                    if r.get("job_id"):
                        try:
                            self.scheduler.remove_job(r["job_id"])
                        except JobLookupError:
                            pass
                reminder_data[session_key] = []
                await self.save(reminder_data)
                return f"已删除所有 {count} 个提醒"

            if content:
                to_delete = []
                for i, r in enumerate(reminders):
                    if content in r.get("text", ""):
                        to_delete.append(i)

                if not to_delete:
                    return f"没有找到包含 '{content}' 的提醒"

                for i in reversed(to_delete):
                    r = reminders[i]
                    if r.get("job_id"):
                        try:
                            self.scheduler.remove_job(r["job_id"])
                        except JobLookupError:
                            pass
                    reminders.pop(i)

                await self.save(reminder_data)
                return f"已删除 {len(to_delete)} 个提醒"

            return "请指定要删除的提醒内容"

        except Exception as e:
            logger.error(f"删除提醒失败: {e}")
            return f"删除提醒失败: {str(e)}"

    async def delete_reminder_by_index(self, event: Any, index: int) -> str:
        """通过索引删除提醒"""
        try:
            session_key = self._get_session_key(event)
            reminder_data = await self.load()

            if session_key not in reminder_data:
                return "当前没有任何提醒"

            reminders = reminder_data[session_key]

            if not reminders:
                return "当前没有任何提醒"

            idx = index - 1
            if idx < 0 or idx >= len(reminders):
                return f"无效的序号：{index}，有效范围：1-{len(reminders)}"

            r = reminders[idx]
            if r.get("job_id"):
                try:
                    self.scheduler.remove_job(r["job_id"])
                except JobLookupError:
                    pass

            reminders.pop(idx)
            await self.save(reminder_data)
            return f"已删除第 {index} 个提醒：{r.get('text', '')}"

        except Exception as e:
            logger.error(f"删除提醒失败: {e}")
            return f"删除提醒失败: {str(e)}"

    async def list_reminders(self, event: Any) -> str:
        """列出提醒"""
        try:
            session_key = self._get_session_key(event)
            reminder_data = await self.load()

            if session_key not in reminder_data:
                return "当前没有任何提醒"

            reminders = reminder_data[session_key]

            if not reminders:
                return "当前没有任何提醒"

            lines = ["当前提醒列表："]
            for i, r in enumerate(reminders, 1):
                text = r.get("text", "")
                dt = r.get("datetime", "")
                repeat = r.get("repeat", "none")
                repeat_str = f" ({repeat})" if repeat != "none" else ""
                lines.append(f"{i}. {text} - {dt}{repeat_str}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"列出提醒失败: {e}")
            return f"列出提醒失败: {str(e)}"

    def _parse_datetime(self, datetime_str: str) -> datetime.datetime | None:
        """解析时间字符串"""
        try:
            datetime_str = datetime_str.strip().replace("：", ":")
            return datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                if ":" in datetime_str and "-" not in datetime_str:
                    today = datetime.datetime.now()
                    hour, minute = map(int, datetime_str.split(":"))
                    dt = today.replace(hour=hour, minute=minute, second=0)
                    if dt < today:
                        dt += datetime.timedelta(days=1)
                    return dt
            except Exception:
                pass
        return None

    def _add_scheduler_job(
        self, session_key: str, reminder: dict, dt: datetime.datetime
    ) -> str:
        """添加调度任务"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        job_id = f"reminder_{session_key}_{timestamp}"

        repeat = reminder.get("repeat", "none")

        if repeat == "daily":
            self.scheduler.add_job(
                self._reminder_callback,
                "cron",
                args=[session_key, reminder],
                hour=dt.hour,
                minute=dt.minute,
                misfire_grace_time=60,
                id=job_id,
            )
        elif repeat == "weekly":
            self.scheduler.add_job(
                self._reminder_callback,
                "cron",
                args=[session_key, reminder],
                day_of_week=dt.weekday(),
                hour=dt.hour,
                minute=dt.minute,
                misfire_grace_time=60,
                id=job_id,
            )
        elif repeat == "monthly":
            self.scheduler.add_job(
                self._reminder_callback,
                "cron",
                args=[session_key, reminder],
                day=dt.day,
                hour=dt.hour,
                minute=dt.minute,
                misfire_grace_time=60,
                id=job_id,
            )
        elif repeat == "yearly":
            self.scheduler.add_job(
                self._reminder_callback,
                "cron",
                args=[session_key, reminder],
                month=dt.month,
                day=dt.day,
                hour=dt.hour,
                minute=dt.minute,
                misfire_grace_time=60,
                id=job_id,
            )
        else:
            self.scheduler.add_job(
                self._reminder_callback,
                "date",
                args=[session_key, reminder],
                run_date=dt,
                misfire_grace_time=60,
                id=job_id,
            )

        logger.info(f"[Reminder] 添加任务: {job_id}")
        return job_id

    async def _reminder_callback(self, session_key: str, reminder: dict) -> None:
        """提醒回调 - 使用官方 API 发送消息"""
        try:
            text = reminder.get("text", "")
            repeat = reminder.get("repeat", "none")

            message = f"提醒：{text}"

            # 使用官方 API 发送消息
            from astrbot.api.event import MessageChain
            from astrbot.core.message.components import Plain

            chain = MessageChain([Plain(text=message)])
            await self.plugin.context.send_message(session_key, chain)

            # 如果不是重复提醒，删除
            if repeat == "none":
                reminder_data = await self.load()
                if session_key in reminder_data:
                    reminders = reminder_data[session_key]
                    for i, r in enumerate(reminders):
                        if r.get("text") == text and r.get("datetime") == reminder.get(
                            "datetime"
                        ):
                            reminders.pop(i)
                            break
                    await self.save(reminder_data)

        except Exception as e:
            logger.error(f"提醒回调失败: {e}")

    async def restore_jobs(self) -> None:
        """恢复调度任务"""
        reminder_data = await self.load()
        for session_key, reminders in reminder_data.items():
            for reminder in reminders:
                if "datetime" not in reminder:
                    continue

                try:
                    dt = datetime.datetime.strptime(
                        reminder["datetime"], "%Y-%m-%d %H:%M"
                    )
                    if dt < datetime.datetime.now():
                        if reminder.get("repeat", "none") == "none":
                            continue
                    self._add_scheduler_job(session_key, reminder, dt)
                except Exception as e:
                    logger.warning(f"恢复任务失败: {e}")
