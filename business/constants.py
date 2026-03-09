"""
业务常量模块

包含插件业务相关的常量定义。

作者: uuutt2023
"""

# ==================== 配置键 ====================

class ConfigKeys:
    """配置键常量"""
    ENABLE = "enable"
    SESSION_ID = "session_id"
    SESSION_TYPE = "session_type"
    PRIVATE_DEFAULT = "private_default"
    GROUP_DEFAULT = "group_default"


class ScheduleKeys:
    """调度配置键常量"""
    SCHEDULE_SETTINGS = "schedule_settings"
    AUTO_TRIGGER_SETTINGS = "auto_trigger_settings"
    ENABLE_AUTO_TRIGGER = "enable_auto_trigger"
    AUTO_TRIGGER_AFTER_MINUTES = "auto_trigger_after_minutes"
    MIN_INTERVAL_MINUTES = "min_interval_minutes"
    MAX_INTERVAL_MINUTES = "max_interval_minutes"
    QUIET_HOURS = "quiet_hours"
    MAX_UNANSWERED_TIMES = "max_unanswered_times"


class ProactiveKeys:
    """主动对话配置键常量"""
    PROACTIVE_PROMPT = "proactive_prompt"
    USE_MINIMAX_FOR_RESPONSE = "use_minimax_for_response"
    GROUP_IDLE_TRIGGER_MINUTES = "group_idle_trigger_minutes"


class MessageKeys:
    """消息配置键常量"""
    TTS_SETTINGS = "tts_settings"
    T2I_SETTINGS = "t2i_settings"


class ReadAirKeys:
    """读空气配置键常量"""
    READ_AIR_SETTINGS = "read_air_settings"
    ENABLE_READ_AIR = "enable_read_air"
    READ_AIR_PROMPT = "read_air_prompt"


class EmojiGateKeys:
    """表情包守门员配置键常量"""
    EMOJI_GATE_ENABLED = "emoji_gate_enabled"
    EMOJI_GATE_RATE = "emoji_gate_rate"


class StorageKeys:
    """存储键常量"""
    LAST_TIME = "last_time"
    UNANSWERED_COUNT = "unanswered_count"
    NEXT_TRIGGER_TIME = "next_trigger_time"


# ==================== 默认值 ====================

class Defaults:
    """默认值常量"""
    # 调度默认
    MIN_INTERVAL_MINUTES = 30
    MAX_INTERVAL_MINUTES = 900
    MAX_UNANSWERED_TIMES = 3
    QUIET_HOURS = "1-7"
    AUTO_TRIGGER_AFTER_MINUTES = 10
    GROUP_IDLE_TRIGGER_MINUTES = 60

    # 表情包守门员默认
    EMOJI_GATE_RATE = 50


__all__ = [
    "ConfigKeys",
    "ScheduleKeys",
    "ProactiveKeys",
    "MessageKeys",
    "ReadAirKeys",
    "EmojiGateKeys",
    "StorageKeys",
    "Defaults",
]
