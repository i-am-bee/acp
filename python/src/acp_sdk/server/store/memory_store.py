import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Generic
from uuid import UUID

from cachetools import TTLCache

from acp_sdk.server.store.store import Store, T


class MemoryStore(Store[T], Generic[T]):
    def __init__(self, *, limit: int, ttl: int | None = None) -> None:
        super().__init__()
        self.cache: TTLCache[str, T] = TTLCache(maxsize=limit, ttl=ttl, timer=datetime.now)
        self.event = asyncio.Event()

    async def get(self, key: UUID) -> T | None:
        return self.cache.get(key)

    async def set(self, key: UUID, value: T) -> None:
        self.cache[key] = value
        self.event.set()

    async def watch(self, key: UUID) -> AsyncIterator[T]:
        while True:
            yield await self.get(key)
            await self.event.wait()
            self.event.clear()
