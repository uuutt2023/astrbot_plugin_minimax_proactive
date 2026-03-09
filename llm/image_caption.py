"""
图片转述工具模块

提供图片描述缓存和转述功能的通用工具类。
支持缓存持久化、过期清理、异步超时控制。

作者: uuutt2023
"""

import asyncio
import time
from typing import Any, Protocol

from astrbot.api import logger as astro_logger

# ==================== 缓存配置 ====================

# 缓存过期时间：一周（7天）
CACHE_EXPIRE_SECONDS = 7 * 24 * 60 * 60


# ==================== 协议定义 ====================


class ImageDescProtocol(Protocol):
    """图片描述协议"""

    async def describe_image(
        self,
        image_url: str,
        prompt: str,
        session_id: str | None = None,
    ) -> str | None: ...


class StorageProtocol(Protocol):
    """存储协议"""

    def get_sync(self, key: str, default: Any = None) -> Any: ...
    def set_sync(self, key: str, value: Any) -> None: ...


# ==================== 图片转述工具类 ====================


class ImageCaptionUtils:
    """图片转述工具类

    提供图片描述缓存和转述功能的通用实现。
    支持缓存持久化、过期清理、异步超时控制。
    """

    # 类级别的缓存（内存缓存）
    _cache: dict[str, dict] = {}

    def __init__(
        self,
        storage: StorageProtocol | None = None,
        timeout: int = 30,
    ) -> None:
        """初始化图片转述工具类

        Args:
            storage: 存储对象，用于持久化缓存
            timeout: 超时时间（秒）
        """
        self._storage = storage
        self._timeout = timeout
        self._initialized = False

    @property
    def timeout(self) -> int:
        """获取超时时间"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        """设置超时时间"""
        self._timeout = max(1, min(value, 300))  # 限制在 1-300 秒之间

    def initialize(self) -> None:
        """初始化，从存储加载缓存"""
        if self._initialized:
            return

        if self._storage:
            self._load_from_storage()

        self._initialized = True

    def _load_from_storage(self) -> None:
        """从存储加载缓存"""
        if not self._storage:
            return

        try:
            cache_data = self._storage.get_sync("image_caption_cache", {})
            if not cache_data:
                return

            now = time.time()
            valid_cache = {}

            for url, data in cache_data.items():
                if isinstance(data, dict):
                    timestamp = data.get("timestamp", 0)
                    if now - timestamp < CACHE_EXPIRE_SECONDS:
                        valid_cache[url] = data
                elif isinstance(data, str):
                    # 兼容旧格式
                    valid_cache[url] = {"caption": data, "timestamp": now}

            ImageCaptionUtils._cache = valid_cache
            self._save_to_storage()

            astro_logger.debug(f"[ImageCaptionUtils] 加载了 {len(valid_cache)} 条图片缓存")
        except Exception as e:
            astro_logger.warning(f"[ImageCaptionUtils] 加载图片缓存失败: {e}")

    def _save_to_storage(self) -> None:
        """保存缓存到存储"""
        if not self._storage:
            return

        try:
            self._storage.set_sync("image_caption_cache", ImageCaptionUtils._cache)
        except Exception as e:
            astro_logger.warning(f"[ImageCaptionUtils] 保存图片缓存失败: {e}")

    def cleanup_expired(self) -> int:
        """清理过期缓存

        Returns:
            清理的缓存数量
        """
        now = time.time()
        expired_keys = [
            url for url, data in ImageCaptionUtils._cache.items()
            if now - data.get("timestamp", 0) >= CACHE_EXPIRE_SECONDS
        ]

        for key in expired_keys:
            del ImageCaptionUtils._cache[key]

        if expired_keys:
            self._save_to_storage()

        return len(expired_keys)

    def get_cached_caption(self, image_url: str) -> str | None:
        """从缓存获取图片描述

        Args:
            image_url: 图片 URL

        Returns:
            缓存的描述文本，如果不存在则返回 None
        """
        if image_url in ImageCaptionUtils._cache:
            cache_entry = ImageCaptionUtils._cache[image_url]
            return cache_entry.get("caption") if isinstance(cache_entry, dict) else cache_entry
        return None

    def set_cached_caption(
        self,
        image_url: str,
        caption: str,
        save: bool = True,
    ) -> None:
        """设置图片描述缓存

        Args:
            image_url: 图片 URL
            caption: 描述文本
            save: 是否立即保存到存储
        """
        ImageCaptionUtils._cache[image_url] = {
            "caption": caption,
            "timestamp": time.time()
        }

        if save:
            self._save_to_storage()

    async def describe_image(
        self,
        llm: ImageDescProtocol,
        image_url: str,
        prompt: str,
        session_id: str | None = None,
    ) -> str | None:
        """描述图片（带缓存和超时控制）

        Args:
            llm: LLM 对象
            image_url: 图片 URL
            prompt: 提示词
            session_id: 会话 ID

        Returns:
            描述文本，失败返回 None
        """
        # 检查缓存
        cached = self.get_cached_caption(image_url)
        if cached:
            astro_logger.info(f"[ImageCaptionUtils] 命中缓存: {image_url[:30]}...")
            return cached

        # 调用 LLM 描述图片
        try:
            description = await asyncio.wait_for(
                llm.describe_image(
                    image_url=image_url,
                    prompt=prompt,
                    session_id=session_id,
                ),
                timeout=self._timeout
            )

            if description:
                self.set_cached_caption(image_url, description.strip())
                astro_logger.info(f"[ImageCaptionUtils] 缓存描述: {image_url[:30]}...")

            return description
        except asyncio.TimeoutError:
            astro_logger.warning(f"[ImageCaptionUtils] 图片转述超时，超过 {self._timeout} 秒")
        except Exception as e:
            astro_logger.error(f"[ImageCaptionUtils] 图片转述失败: {e}")

        return None

    def clear_cache(self) -> None:
        """清空所有缓存"""
        ImageCaptionUtils._cache.clear()
        self._save_to_storage()

    @property
    def cache_size(self) -> int:
        """获取缓存数量"""
        return len(ImageCaptionUtils._cache)


# ==================== 便捷函数 ====================


async def describe_image_with_cache(
    llm: ImageDescProtocol,
    image_url: str,
    prompt: str,
    session_id: str | None = None,
    timeout: int = 30,
    storage: StorageProtocol | None = None,
) -> str | None:
    """便捷函数：描述图片（带缓存）

    Args:
        llm: LLM 对象
        image_url: 图片 URL
        prompt: 提示词
        session_id: 会话 ID
        timeout: 超时时间
        storage: 存储对象

    Returns:
        描述文本，失败返回 None
    """
    utils = ImageCaptionUtils(storage=storage, timeout=timeout)
    utils.initialize()
    return await utils.describe_image(llm, image_url, prompt, session_id)
