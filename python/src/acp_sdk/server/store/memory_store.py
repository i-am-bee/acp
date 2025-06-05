import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Generic

from cachetools import TTLCache

from acp_sdk.server.store.store import Store, StoreModel, T
from acp_sdk.server.store.utils import Stringable


class MemoryStore(Store[T], Generic[T]):
    def __init__(self, *, limit: int, ttl: int | None = None) -> None:
        super().__init__()
        self._cache: TTLCache[str, str] = TTLCache(maxsize=limit, ttl=ttl, timer=datetime.now)
        self._event = asyncio.Event()

    async def get(self, key: Stringable) -> T | None:
        value = self._cache.get(str(key))
        return StoreModel.model_validate_json(value) if value else value

    async def set(self, key: Stringable, value: T | None) -> None:
        if value is None:
            del self._cache[str(key)]
        else:
            self._cache[str(key)] = value.model_dump_json()
        self._event.set()

    async def watch(self, key: Stringable, *, ready: asyncio.Event | None = None) -> AsyncIterator[T | None]:
        if ready:
            ready.set()
        while True:
            await self._event.wait()
            self._event.clear()
            yield await self.get(key)
