import asyncio
from collections.abc import AsyncIterator
from typing import Generic

from redis.asyncio import Redis

from acp_sdk.server.store.store import Store, StoreModel, T
from acp_sdk.server.store.utils import Stringable


class RedisStore(Store[T], Generic[T]):
    def __init__(self, *, redis: Redis) -> None:
        super().__init__()
        self._redis = redis

    async def get(self, key: Stringable) -> T | None:
        value = await self._redis.get(str(key))
        return StoreModel.model_validate_json(value) if value else value

    async def set(self, key: Stringable, value: T | None) -> None:
        if value is None:
            await self._redis.delete(str(key))
        else:
            await self._redis.set(name=str(key), value=value.model_dump_json())

    async def watch(self, key: Stringable, *, ready: asyncio.Event | None = None) -> AsyncIterator[T]:
        await self._redis.config_set("notify-keyspace-events", "KEA")

        pubsub = self._redis.pubsub()
        channel = f"__keyspace@0__:{key!s}"
        await pubsub.subscribe(channel)
        if ready:
            ready.set()
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield await self.get(key)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
