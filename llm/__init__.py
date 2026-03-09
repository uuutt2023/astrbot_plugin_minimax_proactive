"""
LLM 模块

提供 LLM 调用和图片转述功能。

作者: uuutt2023
"""

from .caller import LLMCaller
from .image_caption import (
    CACHE_EXPIRE_SECONDS,
    ImageCaptionUtils,
    ImageDescProtocol,
    StorageProtocol,
    describe_image_with_cache,
)

__all__ = [
    "LLMCaller",
    "ImageCaptionUtils",
    "ImageDescProtocol",
    "StorageProtocol",
    "describe_image_with_cache",
    "CACHE_EXPIRE_SECONDS",
]
