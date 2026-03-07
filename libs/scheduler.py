"""
调度器管理模块

该模块负责管理定时任务调度，支持延迟执行和时间间隔随机化。
支持高并发访问。

作者: uuutt2023
"""

import asyncio
import random
import time
import zoneinfo
from collections.abc import Awaitable, Callable
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class SchedulerManager:
    """调度器管理器

    使用 APScheduler 管理异步定时任务。
    支持高并发访问。
    """

    def __init__(self, timezone_name: str = "UTC") -> None:
        self._scheduler: AsyncIOScheduler | None = None
        self._lock = asyncio.Lock()  # 异步锁
        if timezone_name != "UTC":
            try:
                self._timezone = zoneinfo.ZoneInfo(timezone_name)
            except Exception:
                self._timezone = None
        else:
            self._timezone = None

    @property
    def scheduler(self) -> AsyncIOScheduler:
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler(timezone=None)
        return self._scheduler

    @property
    def timezone(self) -> zoneinfo.ZoneInfo | None:
        return self._timezone

    @timezone.setter
    def timezone(self, timezone_name: str) -> None:
        """设置时区"""
        if timezone_name != "UTC":
            try:
                self._timezone = zoneinfo.ZoneInfo(timezone_name)
            except Exception:
                self._timezone = None
        else:
            self._timezone = None

    def set_timezone(self, timezone_name: str) -> None:
        try:
            self._timezone = zoneinfo.ZoneInfo(timezone_name)
        except Exception:
            self._timezone = None

    def start(self) -> None:
        if self._scheduler and not self._scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler and self._scheduler.running:
            for job in self._scheduler.get_jobs():
                try:
                    job.remove()
                except Exception:
                    pass
            self._scheduler.shutdown(wait=False)

    def add_job(
        self,
        func: Callable[..., Awaitable[None]],
        session_id: str,
        delay_seconds: int,
        min_delay: int = 30,
        max_delay: int = 900,
    ) -> datetime | None:
        interval = random.randint(min_delay, max_delay)
        next_time = time.time() + (delay_seconds if delay_seconds else interval)
        run_date = datetime.fromtimestamp(next_time, tz=self._timezone)

        self.scheduler.add_job(
            func,
            "date",
            run_date=run_date,
            args=[session_id],
            id=session_id,
            replace_existing=True,
            misfire_grace_time=60,
        )
        return run_date

    def remove_job(self, session_id: str) -> None:
        try:
            self.scheduler.remove_job(session_id)
        except Exception:
            pass

    def get_job_time(self, session_id: str) -> datetime | None:
        job = self.scheduler.get_job(session_id)
        return job.next_run_time if job else None
