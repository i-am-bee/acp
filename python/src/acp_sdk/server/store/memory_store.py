import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Generic

from cachetools import TTLCache

from acp_sdk.server.store.store import Store, T
from acp_sdk.server.store.utils import Stringable


class MemoryStore(Store[T], Generic[T]):
    def __init__(self, *, limit: int, ttl: int | None = None) -> None:
        super().__init__()
        self._cache: TTLCache[str, T] = TTLCache(maxsize=limit, ttl=ttl, timer=datetime.now)
        self._event = asyncio.Event()

    async def get(self, key: Stringable) -> T | None:
        value = self._cache.get(str(key))
        return value.model_copy(deep=True) if value else value

    async def set(self, key: Stringable, value: T | None) -> None:
        if value is None:
            del self._cache[str(key)]
        else:
            self._cache[str(key)] = value.model_copy(deep=True)
        self._event.set()

    async def watch(self, key: Stringable, *, ready: asyncio.Event | None = None) -> AsyncIterator[T | None]:
        if ready:
            ready.set()
        while True:
            await self._event.wait()
            self._event.clear()
            yield await self.get(key)
