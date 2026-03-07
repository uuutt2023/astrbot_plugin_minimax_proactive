"""
数据持久化模块

该模块负责将数据持久化到本地 JSON 文件。
使用 orjson 提升序列化/反序列化性能。
支持高并发访问。

作者: uuutt2023
"""

import asyncio
from pathlib import Path
from typing import Any

import orjson


class Storage:
    """数据存储类

    使用 JSON 文件持久化数据（基于 orjson）。
    支持高并发访问。
    """

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._data: dict = {}
        self._lock = asyncio.Lock()  # 异步锁，保证并发安全

    @property
    def data(self) -> dict:
        return self._data

    async def load(self) -> dict:
        async with self._lock:
            if not self.file_path.exists():
                self._data = {}
                return self._data

            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self.file_path.read_bytes)
            self._data = orjson.loads(content)
            return self._data

    async def save(self) -> None:
        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.file_path.parent.mkdir(parents=True, exist_ok=True))
            content = orjson.dumps(
                self._data, option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
            )
            await loop.run_in_executor(None, self.file_path.write_bytes, content)

    def get_sync(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    async def get(self, key: str, default: Any = None) -> Any:
        """异步获取值"""
        async with self._lock:
            return self._data.get(key, default)

    def set_sync(self, key: str, value: Any) -> None:
        self._data[key] = value

    async def set(self, key: str, value: Any) -> None:
        """异步设置值"""
        async with self._lock:
            self._data[key] = value

    def delete_sync(self, key: str) -> None:
        if key in self._data:
            del self._data[key]

    async def delete(self, key: str) -> None:
        """异步删除值"""
        async with self._lock:
            if key in self._data:
                del self._data[key]
