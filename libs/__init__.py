"""
通用工具库模块

该模块提供各种工具函数，包括免打扰时段检测、文本处理、数据存储、调度管理等。

作者: uuutt2023
"""

from .storage import Storage
from .scheduler import SchedulerManager
from .utils import (
    is_quiet_time,
    sanitize_history,
    split_text,
    calc_interval,
    parse_session_id,
    get_session_type,
    format_log,
    has_image_message,
    replace_image_with_text,
)
from .image_caption import ImageCaptionUtils, describe_image_with_cache, CACHE_EXPIRE_SECONDS

# 重新导出 src 中的辅助函数，保持向后兼容
from ..src.helpers import (
    extract_text_from_messages,
    format_session_status,
    format_help_message,
    log_and_return_error,
    check_and_stop_request,
)

from ..src.task_manager import (
    calculate_schedule_intervals,
    calculate_next_trigger_time,
    should_setup_auto_trigger,
    get_session_ids_from_storage,
    is_session_config_valid,
)

from ..src.decorators import (
    log,
    error_handler,
    async_retry,
    timed,
    extract_message_text,
    feature_enabled,
    require_session_config,
    suppress_errors,
)

__all__ = [
    "Storage",
    "SchedulerManager",
    "is_quiet_time",
    "sanitize_history",
    "split_text",
    "calc_interval",
    "parse_session_id",
    "get_session_type",
    "format_log",
    "has_image_message",
    "replace_image_with_text",
    # image_caption
    "ImageCaptionUtils",
    "describe_image_with_cache",
    "CACHE_EXPIRE_SECONDS",
    # helpers
    "extract_text_from_messages",
    "format_session_status",
    "format_help_message",
    "log_and_return_error",
    "check_and_stop_request",
    # task_manager
    "calculate_schedule_intervals",
    "calculate_next_trigger_time",
    "should_setup_auto_trigger",
    "get_session_ids_from_storage",
    "is_session_config_valid",
    # decorators
    "log",
    "error_handler",
    "async_retry",
    "timed",
    "extract_message_text",
    "feature_enabled",
    "require_session_config",
    "suppress_errors",
]
