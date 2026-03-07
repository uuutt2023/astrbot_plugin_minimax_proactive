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
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    return default


# 私聊主动对话默认 Prompt
DEFAULT_PRIVATE_PROACTIVE = load_prompt(
    "private_proactive.txt",
    "请用简短亲切的方式和用户聊天。你可以主动发起话题，但不要太频繁。{{unanswered_count}}表示连续未回复的次数。",
)

# 群聊主动对话默认 Prompt
DEFAULT_GROUP_PROACTIVE = load_prompt(
    "group_proactive.txt",
    "请用简短亲切的方式在群里聊天。你可以主动发起话题，但不要太频繁。{{unanswered_count}}表示连续未回复的次数。",
)

# 读空气默认判断 Prompt
DEFAULT_READ_AIR = load_prompt(
    "read_air.txt",
    "你是一个聊天场合判断助手。判断用户的消息是否需要回复。\n"
    "规则：\n"
    "1. 如果是@机器人、提及机器人名字、或者直接对话，需要回复\n"
    "2. 如果是闲聊且内容与机器人无关，不需要回复\n"
    "3. 如果是疑问句或需要机器人提供信息，需要回复\n"
    "4. 如果是单纯的表情、符号等，不需要回复\n"
    "\n请直接输出 YES 表示需要回复，NO 表示不需要回复，不要输出其他内容。",
)

# 图片描述默认 Prompt
DEFAULT_IMAGE_DESC = load_prompt(
    "image_desc.txt",
    "你是一个图片描述助手。请仔细观察图片中的内容，并用简洁生动的语言描述图片中的关键信息。\n"
    "\n描述要求：\n"
    "1. 重点描述图片的主体内容、人物动作、表情、场景等\n"
    "2. 如果是表情包（meme），请描述出其中的幽默元素或含义\n"
    "3. 如果是文字图片，请提取并描述文字内容\n"
    "4. 保持描述简洁，不超过100字\n"
    "5. 用口语化的方式描述，让聊天更自然\n"
    "\n请直接输出图片描述，不要添加任何前缀或解释。",
)
