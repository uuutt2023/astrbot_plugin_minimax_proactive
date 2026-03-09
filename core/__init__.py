"""
核心模块

包含主动对话核心业务逻辑。

组件:
- ProactiveCore: 核心业务逻辑（使用组件化架构）
- StateManager: 并发安全的状态管理
- ContextProvider: 对话上下文获取
- ProactiveScheduler: 主动聊天调度逻辑
"""

from .context_provider import ContextProvider
from .proactive_core import ProactiveCore
from .proactive_scheduler import ProactiveScheduler
from .state_manager import StateManager

__all__ = [
    "StateManager",
    "ContextProvider",
    "ProactiveScheduler",
    "ProactiveCore",
]
