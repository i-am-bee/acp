from typing import Generic

from acp_sdk.server.store.store import Store, T


class RedisStore(Store[T], Generic[T]):
    async def get(self, key: str) -> T | None:
        pass

    async def set(self, key: str, value: T) -> None:
        pass
