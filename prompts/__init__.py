"""
Prompt 模板模块

包含主动对话和读空气功能使用的 Prompt 模板。
这些文件可以从外部自定义，也可以在配置中覆盖。

作者: uuutt2023
"""

import os

# Prompt 文件路径
PROMPTS_DIR = os.path.dirname(__file__)


def load_prompt(filename: str, default: str = "") -> str:
    """从文件加载 Prompt，如果文件不存在则返回默认值"""
    filepath = os.path.join(PROMPTS_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            return f.read().strip()
    return default


# 私聊主动对话默认 Prompt
DEFAULT_PRIVATE_PROACTIVE = load_prompt(
    "private_proactive.txt",
)

# 群聊主动对话默认 Prompt
DEFAULT_GROUP_PROACTIVE = load_prompt(
    "group_proactive.txt",
)

# 读空气默认判断 Prompt
DEFAULT_READ_AIR = load_prompt(
    "read_air.txt",
)

# 图片描述默认 Prompt
DEFAULT_IMAGE_DESC = load_prompt(
    "image_desc.txt",
)

# 帮助信息
DEFAULT_HELP = load_prompt(
    "help.txt",
)


__all__ = [
    "DEFAULT_PRIVATE_PROACTIVE",
    "DEFAULT_GROUP_PROACTIVE",
    "DEFAULT_READ_AIR",
    "DEFAULT_IMAGE_DESC",
    "DEFAULT_HELP",
    "load_prompt",
]
