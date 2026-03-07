"""
配置获取模块

该模块负责解析和管理插件配置，支持动态配置的私聊和群聊会话配置。

作者: uuutt2023
"""

__all__ = ["ConfigManager"]


class ConfigManager:
    """配置管理器

    负责从配置中提取和匹配会话配置。
    支持私聊和群聊两种会话类型的配置管理。
    支持全局默认设置与单独会话配置的合并。
    """

    def __init__(self, config) -> None:
        self._config = config
        self._config_dict = config if hasattr(config, "get") else {}

    @property
    def debug_mode(self) -> bool:
        """调试模式"""
        return self._config.get("debug_mode", False)
    
    @property
    def llm_settings(self) -> dict:
        """LLM 设置"""
        # 兼容新旧配置结构
        if "llm_settings" in self._config:
            return self._config.get("llm_settings", {}) or {}
        
        # 新扁平化结构
        # use_astrbot_provider 是字符串（provider名称）或空字符串
        provider = self._config.get("use_astrbot_provider", "")
        
        # use_minimax_for_response 是布尔值，表示是否用MiniMax API替换默认对话
        use_minimax = self._config.get("use_minimax_for_response", False)
        
        # 调试模式
        debug = self._config.get("debug_mode", False)
        
        # 逻辑：
        # 1. 如果选择了AstrBot provider (provider不为空)，优先使用AstrBot
        # 2. 如果没有选择AstrBot provider且use_minimax为True，使用MiniMax API
        # 3. 否则使用默认行为
        use_astrbot = bool(provider)
        
        return {
            "use_astrbot_provider": use_astrbot,
            "selected_provider": provider,  # 保存用户选择的provider名称
            "use_minimax_for_response": use_minimax,  # 保存是否使用MiniMax替换默认对话
            "debug_mode": debug,
            "minimax_settings": {
                "api_key": self._config.get("minimax_api_key", ""),
                "base_url": self._config.get("minimax_base_url", "https://api.minimax.chat/v1"),
                "model": self._config.get("minimax_model", "abab6.5s-chat"),
                "temperature": self._config.get("minimax_temperature", 0.7),
                "max_tokens": self._config.get("minimax_max_tokens", 4096),
            }
        }

    @property
    def minimax_settings(self) -> dict:
        """MiniMax API 设置（兼容旧配置）"""
        return self.llm_settings.get("minimax_settings", {}) or {}

    @property
    def private_sessions(self) -> list:
        return self._config.get("private_sessions", []) or []

    @property
    def group_sessions(self) -> list:
        return self._config.get("group_sessions", []) or []

    @property
    def private_default_settings(self) -> dict:
        """私聊全局默认设置"""
        # 兼容新旧配置结构
        if "private_default_settings" in self._config:
            return self._config.get("private_default_settings", {}) or {}
        
        # 新扁平化结构
        return {
            "enable": self._config.get("private_enable", False),
            "proactive_prompt": self._config.get("private_prompt", ""),
            "use_minimax_for_response": self._config.get("private_use_minimax", False),
            "read_air_settings": {
                "enable_read_air": self._config.get("private_read_air", False),
                "read_air_prompt": self._config.get("private_read_air_prompt", ""),
                "read_air_provider": self._config.get("private_read_air_provider", ""),
            },
            "schedule_settings": {
                "min_interval_minutes": self._config.get("private_min_interval", 30),
                "max_interval_minutes": self._config.get("private_max_interval", 900),
                "max_unanswered_times": self._config.get("private_max_times", 3),
                "quiet_hours": self._config.get("private_quiet_hours", "1-7"),
            },
            "auto_trigger_settings": {
                "enable_auto_trigger": self._config.get("private_auto_trigger", False),
                "auto_trigger_after_minutes": self._config.get("private_auto_delay", 5),
            },
            "tts_settings": {
                "enable_tts": self._config.get("private_tts", False),
                "always_send_text": self._config.get("private_tts_with_text", True),
            },
            "t2i_settings": {
                "enable_t2i": self._config.get("private_t2i", False),
                "t2i_char_threshold": self._config.get("private_t2i_threshold", 500),
            },
            "image_desc_settings": {
                "enable_image_desc": self._config.get("private_image_desc", False),
                "image_desc_prompt": self._config.get("private_image_desc_prompt", ""),
                "image_desc_provider": self._config.get("private_image_desc_provider", ""),
            },
        }

    @property
    def group_default_settings(self) -> dict:
        """群聊全局默认设置"""
        # 兼容新旧配置结构
        if "group_default_settings" in self._config:
            return self._config.get("group_default_settings", {}) or {}
        
        # 新扁平化结构
        return {
            "enable": self._config.get("group_enable", False),
            "proactive_prompt": self._config.get("group_prompt", ""),
            "use_minimax_for_response": self._config.get("group_use_minimax", False),
            "read_air_settings": {
                "enable_read_air": self._config.get("group_read_air", False),
                "read_air_prompt": self._config.get("group_read_air_prompt", ""),
                "read_air_provider": self._config.get("group_read_air_provider", ""),
            },
            "schedule_settings": {
                "min_interval_minutes": self._config.get("group_min_interval", 30),
                "max_interval_minutes": self._config.get("group_max_interval", 900),
                "max_unanswered_times": self._config.get("group_max_times", 3),
                "quiet_hours": self._config.get("group_quiet_hours", "1-7"),
            },
            "auto_trigger_settings": {
                "enable_auto_trigger": self._config.get("group_auto_trigger", False),
                "auto_trigger_after_minutes": self._config.get("group_auto_delay", 5),
            },
            "group_idle_trigger_minutes": self._config.get("group_idle_trigger", 10),
            "tts_settings": {
                "enable_tts": self._config.get("group_tts", False),
                "always_send_text": self._config.get("group_tts_with_text", True),
            },
            "t2i_settings": {
                "enable_t2i": self._config.get("group_t2i", False),
                "t2i_char_threshold": self._config.get("group_t2i_threshold", 500),
            },
            "image_desc_settings": {
                "enable_image_desc": self._config.get("group_image_desc", False),
                "image_desc_prompt": self._config.get("group_image_desc_prompt", ""),
                "image_desc_provider": self._config.get("group_image_desc_provider", ""),
            },
        }

    @property
    def proactive_chat_enabled(self) -> bool:
        return self._config.get("enable_proactive_chat", True)

    @property
    def reminder_enabled(self) -> bool:
        return self._config.get("enable_reminder", True)

    def get_session_config(self, session_id: str) -> dict | None:
        parsed = self._parse_session_id(session_id)
        if not parsed:
            return None

        _, msg_type, target_id = parsed

        if "Friend" in msg_type or "Private" in msg_type:
            return self._get_private_config(target_id)
        if "Group" in msg_type:
            return self._get_group_config(target_id)
        return None

    def _get_private_config(self, target_id: str) -> dict | None:
        sessions = self.private_sessions
        default_cfg = self.private_default_settings

        # 先查找单独会话配置
        if isinstance(sessions, list):
            for cfg in sessions:
                if not isinstance(cfg, dict):
                    continue
                sid = str(cfg.get("session_id", ""))
                if sid and (target_id == sid or target_id.endswith(f":{sid}")):
                    if cfg.get("enable"):
                        # 合并全局默认配置
                        merged = self._merge_with_default(cfg, default_cfg)
                        return self._add_meta(merged, "private")

        # 回退到全局默认配置
        if default_cfg.get("enable"):
            return self._add_meta(default_cfg.copy(), "private")

        return None

    def _get_group_config(self, target_id: str) -> dict | None:
        sessions = self.group_sessions
        default_cfg = self.group_default_settings

        # 先查找单独会话配置
        if isinstance(sessions, list):
            for cfg in sessions:
                if not isinstance(cfg, dict):
                    continue
                sid = str(cfg.get("session_id", ""))
                if sid and (target_id == sid or target_id.endswith(f":{sid}")):
                    if cfg.get("enable"):
                        # 合并全局默认配置
                        merged = self._merge_with_default(cfg, default_cfg)
                        return self._add_meta(merged, "group")

        # 回退到全局默认配置
        if default_cfg.get("enable"):
            return self._add_meta(default_cfg.copy(), "group")

        return None

    def _merge_with_default(self, session_cfg: dict, default_cfg: dict) -> dict:
        """将会话配置与全局默认配置合并，会话配置优先"""
        if not default_cfg:
            return session_cfg.copy()

        result = default_cfg.copy()
        # 遍历会话配置，替换默认值
        for key, value in session_cfg.items():
            if value is not None and value != "" and value != {}:
                result[key] = value
        return result

    def _add_meta(self, cfg: dict, session_type: str) -> dict:
        result = cfg.copy()
        result["_session_type"] = session_type
        result["_session_name"] = cfg.get("session_name", "")
        return result

    def _parse_session_id(self, session_id: str) -> tuple[str, str, str] | None:
        if not isinstance(session_id, str):
            return None

        for msg_type in [
            "FriendMessage",
            "GroupMessage",
            "PrivateMessage",
            "GuildMessage",
        ]:
            pattern = f":{msg_type}:"
            idx = session_id.find(pattern)
            if idx != -1:
                return session_id[:idx], msg_type, session_id[idx + len(pattern) :]

        parts = session_id.split(":")
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        if len(parts) > 3:
            return ":".join(parts[:-2]), parts[-2], parts[-1]
        return None
