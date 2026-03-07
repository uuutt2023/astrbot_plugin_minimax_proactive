# pyright: reportReturnType=false
"""
自定义注解模块

提供各种装饰器用于优化代码结构：
使用 tenacity 库简化重试逻辑。

作者: uuutt2023
"""

import asyncio
import functools
import time
from typing import Any, Callable

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from astrbot.api import logger


# ==================== 日志注解 ====================


def log(message: str = "", level: str = "info"):
    """日志记录装饰器

    Args:
        message: 日志消息模板
        level: 日志级别 (debug/info/warning/error)
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                msg = message or f"执行 {func.__name__}"
                log_func = getattr(logger, level, logger.info)
                log_func(f"[MiniMaxProactive] {msg}")
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[MiniMaxProactive] {msg} 失败: {e}")
                    raise

            return async_wrapper
        else:

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

            return sync_wrapper

    return decorator


# ==================== 错误处理注解 ====================


def error_handler(default_return: Any = None, log_error: bool = True):
    """错误处理装饰器

    Args:
        default_return: 错误时的默认返回值
        log_error: 是否记录错误日志
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if log_error:
                        logger.error(
                            f"[MiniMaxProactive] {func.__name__} 执行错误: {e}"
                        )
                    return default_return

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if log_error:
                        logger.error(
                            f"[MiniMaxProactive] {func.__name__} 执行错误: {e}"
                        )
                    return default_return

            return sync_wrapper

    return decorator


# ==================== 异步重试注解 (使用 tenacity) ====================


def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """异步重试装饰器 (基于 tenacity)

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff, min=delay, max=delay * 10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda retry_state: (
            logger.warning(
                f"[MiniMaxProactive] 第 {retry_state.attempt_number} 次尝试失败, "
                f"{retry_state.next_action.sleep}秒后重试..."
            )
            if retry_state.outcome and not retry_state.outcome.success
            else None
        ),
    )


# ==================== 性能计时注解 ====================


def timed(logger_msg: str = ""):
    """性能计时装饰器

    Args:
        logger_msg: 日志消息前缀
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = time.perf_counter() - start_time
                    logger.debug(
                        f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s"
                    )
                    return result
                except Exception:
                    elapsed = time.perf_counter() - start_time
                    logger.warning(
                        f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s (失败)"
                    )
                    raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.perf_counter() - start_time
                    logger.debug(
                        f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s"
                    )
                    return result
                except Exception:
                    elapsed = time.perf_counter() - start_time
                    logger.warning(
                        f"[MiniMaxProactive] {logger_msg or func.__name__} 耗时: {elapsed:.3f}s (失败)"
                    )
                    raise

            return sync_wrapper

    return decorator


# ==================== 消息提取装饰器 ====================


def extract_message_text(field: str = "messages"):
    """消息提取装饰器

    自动从事件中提取消息文本并作为参数传入。

    Args:
        field: 要替换的参数名

    Example:
        @extract_message_text()
        async def handle(text: str, event): ...
    """

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # 查找 event 参数
            event = kwargs.get("event") or (args[0] if args else None)
            if event and hasattr(event, "get_messages"):
                messages = event.get_messages()
                if messages:
                    from .helpers import extract_text_from_messages

                    text = extract_text_from_messages(messages)
                    kwargs[field] = text
            return await func(*args, **kwargs)

        return async_wrapper

    return decorator


# ==================== 功能开关装饰器 ====================


def feature_enabled(feature_check_func):
    """功能开关装饰器

    在执行前检查功能是否启用，未启用时返回提示信息。

    Args:
        feature_check_func: 返回 bool 的函数

    Example:
        @feature_enabled(lambda self: self._is_reminder_enabled())
        async def cmd(self, event): ...
    """

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            if not feature_check_func(*args, **kwargs):
                return "功能已关闭"
            return await func(*args, **kwargs)

        return async_wrapper

    return decorator


# ==================== 会话验证装饰器 ====================


def require_session_config(session_param: str = "session_id"):
    """会话配置验证装饰器

    自动获取会话配置并验证其有效性。

    Args:
        session_param: 会话ID参数名

    Example:
        @require_session_config()
        async def handle(cfg, session_id): ...
    """

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # 获取 self
            self_obj = args[0] if args else None
            if not hasattr(self_obj, "_services"):
                return await func(*args, **kwargs)

            # 获取 session_id
            session_id = kwargs.get(session_param)
            if not session_id:
                event = kwargs.get("event")
                if event and hasattr(event, "unified_msg_origin"):
                    session_id = event.unified_msg_origin

            if not session_id:
                return await func(*args, **kwargs)

            # 获取配置
            cfg = self_obj._services.get_session_config(session_id)
            if not cfg:
                return None

            # 替换或添加 cfg 参数
            kwargs["cfg"] = cfg
            return await func(*args, **kwargs)

        return async_wrapper

    return decorator


# ==================== 异常捕获装饰器 ====================


def suppress_errors(default_return=None, log_level: str = "error"):
    """异常抑制装饰器

    捕获异常并返回默认值，同时记录日志。

    Args:
        default_return: 异常时的默认返回值
        log_level: 日志级别

    Example:
        @suppress_errors(default_return="操作失败")
        async def risky_operation(): ...
    """

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            from astrbot.api import logger

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_func = getattr(logger, log_level, logger.error)
                log_func(f"[MiniMaxProactive] {func.__name__} 执行异常: {e}")
                return default_return

        return async_wrapper

    return decorator


__all__ = [
    "log",
    "error_handler",
    "async_retry",
    "timed",
    # 新增装饰器
    "extract_message_text",
    "feature_enabled",
    "require_session_config",
    "suppress_errors",
    "debug",
    "DebugLog",
    "get_debug_logger",
]


# ==================== 调试日志装饰器 ====================


class DebugLog:
    """调试日志类
    
    用于控制调试日志的输出，包含一个全局的调试开关。
    可以通过实例方法设置debug_mode来控制输出。
    """
    
    _instance = None
    _debug = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def enabled(self) -> bool:
        """是否启用调试模式"""
        return self._debug
    
    @enabled.setter
    def enabled(self, value: bool):
        """设置调试模式"""
        self._debug = value
    
    def set_debug_mode(self, debug: bool):
        """设置调试模式"""
        self._debug = debug
        if self._debug:
            logger.info("[MiniMaxProactive] 调试模式已开启")
    
    def is_debug(self) -> bool:
        """检查是否处于调试模式"""
        return self._debug


# 全局调试日志实例
_debug_logger = DebugLog()


def get_debug_logger() -> DebugLog:
    """获取全局调试日志实例"""
    return _debug_logger


def debug(message: str = "", log_args: bool = True, log_result: bool = True):
    """调试日志装饰器
    
    仅在debug_mode为True时输出日志。支持输出调用前参数和调用后返回值。
    日志格式：[插件名][DEBUG][函数名] 参数/返回值
    
    Args:
        message: 日志消息模板，默认使用函数名
        log_args: 是否输出调用参数
        log_result: 是否输出返回值
    """
    
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                func_name = message or func.__name__
                
                # 输出参数
                if _debug_logger.enabled and log_args:
                    safe_args = []
                    for i, arg in enumerate(args):
                        if i == 0:
                            continue
                        if hasattr(arg, '__dict__'):
                            safe_args.append(arg.__class__.__name__)
                        elif isinstance(arg, str) and len(arg) > 100:
                            safe_args.append(f"<str:len={len(arg)}>")
                        else:
                            safe_args.append(repr(arg))
                    
                    if safe_args:
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 参数: {safe_args}")
                    elif kwargs:
                        safe_kwargs = {}
                        for k, v in kwargs.items():
                            if isinstance(v, str) and len(v) > 100:
                                safe_kwargs[k] = f"<str:len={len(v)}>"
                            elif hasattr(v, '__dict__'):
                                safe_kwargs[k] = v.__class__.__name__
                            else:
                                safe_kwargs[k] = repr(v)
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 参数: {safe_kwargs}")
                    else:
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 参数: (无)")
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # 输出返回值
                    if _debug_logger.enabled and log_result:
                        if isinstance(result, str) and len(result) > 100:
                            logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 返回值: <str:len={len(result)}>")
                        elif result is None:
                            logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 返回值: None")
                        else:
                            logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 返回值: {repr(result)[:200]}")
                    
                    return result
                    
                except Exception as e:
                    if _debug_logger.enabled:
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 异常: {e}")
                    raise
            
            return async_wrapper
        else:
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                func_name = message or func.__name__
                
                # 输出参数
                if _debug_logger.enabled and log_args:
                    safe_args = []
                    for i, arg in enumerate(args):
                        if i == 0:
                            continue
                        if hasattr(arg, '__dict__'):
                            safe_args.append(arg.__class__.__name__)
                        elif isinstance(arg, str) and len(arg) > 100:
                            safe_args.append(f"<str:len={len(arg)}>")
                        else:
                            safe_args.append(repr(arg))
                    
                    if safe_args:
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 参数: {safe_args}")
                    elif kwargs:
                        safe_kwargs = {}
                        for k, v in kwargs.items():
                            if isinstance(v, str) and len(v) > 100:
                                safe_kwargs[k] = f"<str:len={len(v)}>"
                            elif hasattr(v, '__dict__'):
                                safe_kwargs[k] = v.__class__.__name__
                            else:
                                safe_kwargs[k] = repr(v)
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 参数: {safe_kwargs}")
                    else:
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 参数: (无)")
                
                try:
                    result = func(*args, **kwargs)
                    
                    # 输出返回值
                    if _debug_logger.enabled and log_result:
                        if isinstance(result, str) and len(result) > 100:
                            logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 返回值: <str:len={len(result)}>")
                        elif result is None:
                            logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 返回值: None")
                        else:
                            logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 返回值: {repr(result)[:200]}")
                    
                    return result
                    
                except Exception as e:
                    if _debug_logger.enabled:
                        logger.info(f"[MiniMaxProactive][DEBUG][{func_name}] 异常: {e}")
                    raise
            
            return sync_wrapper
    
    return decorator
