"""
配置键枚举模块

定义所有配置键和存储键的枚举类型，方便维护和开发。

作者: uuutt2023

注意: 消息类型、权限类型等通用枚举请使用官方 API:
- EventMessageType: from astrbot.api.event.filter import EventMessageType
- MessageType: from astrbot.core.platform.message_type import MessageType
- PermissionType: from astrbot.api.event.filter import PermissionType
"""

from enum import Enum


# ==================== 存储键 ====================


class StorageKeys(str, Enum):
    """存储数据键枚举"""

    LAST_TIME = "last_time"
    UNANSWERED_COUNT = "unanswered_count"
    NEXT_TRIGGER_TIME = "next_trigger_time"


# ==================== 配置键 - 通用 ====================


class ConfigKeys(str, Enum):
    """通用配置键枚举"""

    ENABLE = "enable"
    SESSION_ID = "session_id"
    SESSION_TYPE = "_session_type"
    SESSION_NAME = "_session_name"


# ==================== 配置键 - 调度 ====================


class ScheduleKeys(str, Enum):
    """调度配置键枚举"""

    SCHEDULE_SETTINGS = "schedule_settings"
    MIN_INTERVAL_MINUTES = "min_interval_minutes"
    MAX_INTERVAL_MINUTES = "max_interval_minutes"
    QUIET_HOURS = "quiet_hours"
    MAX_UNANSWERED_TIMES = "max_unanswered_times"
    AUTO_TRIGGER_SETTINGS = "auto_trigger_settings"
    ENABLE_AUTO_TRIGGER = "enable_auto_trigger"
    AUTO_TRIGGER_AFTER_MINUTES = "auto_trigger_after_minutes"


# ==================== 配置键 - 消息发送 ====================


class MessageKeys(str, Enum):
    """消息配置键枚举"""

    TTS_SETTINGS = "tts_settings"
    T2I_SETTINGS = "t2i_settings"

    # TTS
    ENABLE_TTS = "enable_tts"
    ALWAYS_SEND_TEXT = "always_send_text"

    # 文转图
    ENABLE_T2I = "enable_t2i"
    T2I_CHAR_THRESHOLD = "t2i_char_threshold"
    HTML_TEMPLATE = "html_template"
    T2I_OPTIONS = "t2i_options"


# ==================== 配置键 - 主动对话 ====================


class ProactiveKeys(str, Enum):
    """主动对话配置键枚举"""

    PROACTIVE_PROMPT = "proactive_prompt"
    USE_MINIMAX_FOR_RESPONSE = "use_minimax_for_response"
    GROUP_IDLE_TRIGGER_MINUTES = "group_idle_trigger_minutes"


# ==================== 配置键 - 读空气 ====================


class ReadAirKeys(str, Enum):
    """读空气配置键枚举"""

    READ_AIR_SETTINGS = "read_air_settings"
    ENABLE_READ_AIR = "enable_read_air"
    READ_AIR_PROMPT = "read_air_prompt"


# ==================== 配置键 - 表情包转述 ====================


class ImageDescKeys(str, Enum):
    """表情包转述配置键枚举"""

    IMAGE_DESC_SETTINGS = "image_desc_settings"
    ENABLE_IMAGE_DESC = "enable_image_desc"
    IMAGE_DESC_PROMPT = "image_desc_prompt"


# ==================== 配置键 - LLM ====================


class LLMKeys(str, Enum):
    """LLM配置键枚举"""

    LLM_SETTINGS = "llm_settings"
    USE_BUILTIN_LLM = "use_builtin_llm"
    MINIMAX_API_KEY = "minimax_api_key"
    MINIMAX_GROUP_ID = "minimax_group_id"
    MINIMAX_MODEL = "minimax_model"


# ==================== 配置键 - 提醒 ====================


class ReminderKeys(str, Enum):
    """提醒配置键枚举"""

    REMINDER_ENABLED = "reminder_enabled"


# ==================== 官方枚举导入 ====================

# 消息类型枚举 (推荐使用)
# from astrbot.api.event.filter import EventMessageType
#   - EventMessageType.PRIVATE_MESSAGE
#   - EventMessageType.GROUP_MESSAGE
#   - EventMessageType.OTHER_MESSAGE

# 平台消息类型 (底层枚举)
# from astrbot.core.platform.message_type import MessageType
#   - MessageType.GROUP_MESSAGE
#   - MessageType.FRIEND_MESSAGE
#   - MessageType.OTHER_MESSAGE

# 权限类型枚举
# from astrbot.api.event.filter import PermissionType
#   - PermissionType.ADMIN
#   - PermissionType.MEMBER


# ==================== 默认值 ====================


class Defaults:
    """默认值常量"""

    # 调度
    MIN_INTERVAL_MINUTES = 30
    MAX_INTERVAL_MINUTES = 900
    QUIET_HOURS = "1-7"
    MAX_UNANSWERED_TIMES = 3
    AUTO_TRIGGER_AFTER_MINUTES = 5

    # 消息
    TTS_ENABLED = True
    ALWAYS_SEND_TEXT = True
    T2I_ENABLED = False
    T2I_CHAR_THRESHOLD = 500

    # 群聊
    GROUP_IDLE_TRIGGER_MINUTES = 10
