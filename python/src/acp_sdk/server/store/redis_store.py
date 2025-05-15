from collections.abc import AsyncIterator
from typing import Generic
from uuid import UUID

from redis.asyncio import Redis

from acp_sdk.server.store.store import Store, T


class RedisStore(Store[T], Generic[T]):
    def __init__(self, *, model: type[T], redis: Redis) -> None:
        super().__init__()
        self.model = model
        self.redis = redis

    async def get(self, key: UUID) -> T | None:
        data = await self.redis.get(str(key))
        return self.model.model_validate_json(data)

    async def set(self, key: UUID, value: T) -> None:
        await self.redis.set(name=str(key), value=value.model_dump_json())

    async def watch(self, key: UUID) -> AsyncIterator[T]:
        await self.redis.config_set("notify-keyspace-events", "KEA")

        pubsub = self.redis.pubsub()
        channel = f"__keyspace@0__:{key!s}"
        await pubsub.subscribe(channel)
        try:
            yield await self.get(key)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield await self.get(key)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
