"""
配置管理器模块

管理插件配置。

作者: uuutt2023
"""

from typing import Any

from .constants import Defaults


class ConfigManager:
    """配置管理器"""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    @property
    def proactive_chat_enabled(self) -> bool:
        """获取主动对话是否启用"""
        return self._config.get("enable_proactive_chat", True)

    @property
    def reminder_enabled(self) -> bool:
        """获取提醒功能是否启用"""
        return self._config.get("enable_reminder", True)

    @property
    def llm_settings(self) -> dict[str, Any]:
        """获取 LLM 设置"""
        return self._config.get("llm", {})

    @property
    def private_default_settings(self) -> dict[str, Any]:
        """获取私聊默认设置"""
        return self._build_private_settings()

    @property
    def group_default_settings(self) -> dict[str, Any]:
        """获取群聊默认设置"""
        return self._build_group_settings()

    @property
    def private_sessions(self) -> list[dict[str, Any]]:
        """获取私聊会话列表"""
        return self._config.get("private_sessions", [])

    @property
    def group_sessions(self) -> list[dict[str, Any]]:
        """获取群聊会话列表"""
        return self._config.get("group_sessions", [])

    def get_session_config(self, session_id: str) -> dict[str, Any] | None:
        """获取会话配置"""
        # 解析会话ID
        parts = session_id.split(":")
        if len(parts) < 3:
            return None

        msg_type = parts[1]
        target_id = parts[2] if len(parts) > 2 else None

        # 优先查找单独的会话配置
        sessions = self.private_sessions if "Friend" in msg_type or "Private" in msg_type else self.group_sessions

        for session in sessions:
            if session.get("session_id") == target_id:
                return session

        # 使用默认配置
        if "Friend" in msg_type or "Private" in msg_type:
            return self.private_default_settings
        elif "Group" in msg_type:
            return self.group_default_settings

        return None

    def _build_private_settings(self) -> dict[str, Any]:
        """构建私聊默认设置"""
        return {
            "enable": self._config.get("private_enable", True),
            "schedule_settings": {
                "min_interval_minutes": self._config.get("private_min_interval", Defaults.MIN_INTERVAL_MINUTES),
                "max_interval_minutes": self._config.get("private_max_interval", Defaults.MAX_INTERVAL_MINUTES),
                "max_unanswered_times": self._config.get("private_max_unanswered", Defaults.MAX_UNANSWERED_TIMES),
                "quiet_hours": self._config.get("private_quiet_hours", Defaults.QUIET_HOURS),
            },
            "auto_trigger_settings": {
                "enable_auto_trigger": self._config.get("private_auto_trigger", False),
                "auto_trigger_after_minutes": self._config.get("private_auto_trigger_after", Defaults.AUTO_TRIGGER_AFTER_MINUTES),
            },
            "emoji_gate_enabled": self._config.get("private_emoji_gate", False),
            "emoji_gate_rate": self._config.get("private_emoji_gate_rate", Defaults.EMOJI_GATE_RATE),
            "session_type": "private",
        }

    def _build_group_settings(self) -> dict[str, Any]:
        """构建群聊默认设置"""
        return {
            "enable": self._config.get("group_enable", True),
            "schedule_settings": {
                "min_interval_minutes": self._config.get("group_min_interval", Defaults.MIN_INTERVAL_MINUTES),
                "max_interval_minutes": self._config.get("group_max_interval", Defaults.MAX_INTERVAL_MINUTES),
                "max_unanswered_times": self._config.get("group_max_unanswered", Defaults.MAX_UNANSWERED_TIMES),
                "quiet_hours": self._config.get("group_quiet_hours", Defaults.QUIET_HOURS),
            },
            "auto_trigger_settings": {
                "enable_auto_trigger": self._config.get("group_auto_trigger", False),
                "auto_trigger_after_minutes": self._config.get("group_auto_trigger_after", Defaults.AUTO_TRIGGER_AFTER_MINUTES),
            },
            "emoji_gate_enabled": self._config.get("group_emoji_gate", False),
            "emoji_gate_rate": self._config.get("group_emoji_gate_rate", Defaults.EMOJI_GATE_RATE),
            "session_type": "group",
        }
