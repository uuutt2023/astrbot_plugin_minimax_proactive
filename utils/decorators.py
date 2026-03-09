# pyright: reportReturnType=false
"""
自定义注解模块

提供各种装饰器用于优化代码结构。

作者: uuutt2023
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from astrbot.api import logger

P = ParamSpec("P")
R = TypeVar("R")


# ==================== 辅助函数 ====================


def _is_async_func(func: Callable[..., Any]) -> bool:
    """检查是否是异步函数"""
    return asyncio.iscoroutinefunction(func)


def _format_arg(arg: Any, skip_first: bool = False, index: int = 0) -> str | None:
    """格式化参数为安全字符串"""
    if skip_first and index == 0:
        return None
    if hasattr(arg, "__dict__"):
        return arg.__class__.__name__
    if isinstance(arg, str) and len(arg) > 100:
        return f"<str:len={len(arg)}>"
    result: str = repr(arg)
    return result


def _safe_args_to_str(args: tuple[Any, ...], kwargs: dict[str, Any], skip_first: bool = True) -> str:
    """将参数转换为安全的日志字符串"""
    safe_args = []
    for i, arg in enumerate(args):
        formatted = _format_arg(arg, skip_first, i)
        if formatted:
            safe_args.append(formatted)

    if safe_args:
        return str(safe_args)

    if kwargs:
        safe_kwargs = {
            k: v if not isinstance(v, str) or len(v) <= 100 else f"<str:len={len(v)}>"
            for k, v in kwargs.items()
        }
        return str(safe_kwargs)

    return "(无)"


def _safe_result_to_str(result: Any) -> str:
    """将返回值转换为安全的日志字符串"""
    if result is None:
        return "None"
    if isinstance(result, str) and len(result) > 100:
        return f"<str:len={len(result)}>"
    return repr(result)[:200]


# ==================== 日志注解 ====================


def log(message: str = "", level: str = "info"):
    """日志记录装饰器"""

    def decorator(func: Callable) -> Callable:
        is_async = _is_async_func(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            msg = message or f"执行 {func.__name__}"
            log_func = getattr(logger, level, logger.info)
            log_func(f"[MiniMaxProactive] [{level.upper()}] {func.__name__} {msg}")
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[MiniMaxProactive] [ERROR] {func.__name__} {msg} 失败: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            msg = message or f"执行 {func.__name__}"
            log_func = getattr(logger, level, logger.info)
            log_func(f"[MiniMaxProactive] {msg}")
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[MiniMaxProactive] {msg} 失败: {e}")
                raise

        return async_wrapper if is_async else sync_wrapper

    return decorator


# ==================== 错误处理注解 ====================


def error_handler(default_return: Any = None, log_error: bool = True):
    """错误处理装饰器"""

    def decorator(func: Callable) -> Callable:
        is_async = _is_async_func(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"[MiniMaxProactive] {func.__name__} 执行错误: {e}")
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"[MiniMaxProactive] {func.__name__} 执行错误: {e}")
                return default_return

        return async_wrapper if is_async else sync_wrapper

    return decorator


# ==================== 异步重试注解 ====================


def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """异步重试装饰器"""
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff, min=delay, max=delay * 10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )


# ==================== 性能计时注解 ====================


def timed(logger_msg: str = ""):
    """性能计时装饰器"""

    def decorator(func: Callable) -> Callable:
        is_async = _is_async_func(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.debug(f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s")
                return result
            except Exception:
                elapsed = time.perf_counter() - start_time
                logger.warning(f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s (失败)")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.debug(f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s")
                return result
            except Exception:
                elapsed = time.perf_counter() - start_time
                logger.warning(f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s (失败)")
                raise

        return async_wrapper if is_async else sync_wrapper

    return decorator


# ==================== 功能开关装饰器 ====================


def feature_enabled(feature_check_func):
    """功能开关装饰器"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            if not feature_check_func(*args, **kwargs):
                return "功能已关闭"
            return await func(*args, **kwargs)

        return async_wrapper

    return decorator


# ==================== 事件提取装饰器 ====================


def extract_event_param(event_name: str = "event", request_name: str = "request"):
    """事件参数提取装饰器

    自动从 args/kwargs 中提取事件和请求对象
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        from astrbot.api.event import AstrMessageEvent

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 提取事件
            event = kwargs.get(event_name)
            if not event:
                for arg in args:
                    if isinstance(arg, AstrMessageEvent):
                        event = arg
                        break
                kwargs[event_name] = event

            # 提取请求
            if request_name not in kwargs:
                kwargs[request_name] = kwargs.get("request") or (args[1] if len(args) > 1 else None)

            return await func(*args, **kwargs)

        return async_wrapper
    return decorator


# ==================== 提醒管理器装饰器 ====================


def with_reminder(loaded_name: str = "_reminder_loaded", restore: bool = False):
    """提醒管理器自动加载装饰器

    Args:
        loaded_name: 标记参数名
        restore: 是否在结束后恢复任务
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 检查功能是否启用
            if not self._is_reminder_enabled():
                return "提醒功能已关闭"

            # 加载提醒管理器
            await self._reminder_mgr.load()
            kwargs[loaded_name] = True

            # 执行原函数
            result = await func(self, *args, **kwargs)

            # 恢复任务
            if restore:
                await self._reminder_mgr.restore_jobs()

            return result

        return wrapper
    return decorator


__all__ = [
    "log",
    "error_handler",
    "async_retry",
    "timed",
    "feature_enabled",
]
