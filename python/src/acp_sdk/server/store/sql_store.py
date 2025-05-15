from typing import Generic
from uuid import UUID

from acp_sdk.server.store.store import Store, T


class SQLStore(Store[T], Generic[T]):
    async def get(self, key: UUID) -> T | None:
        pass

    async def set(self, key: UUID, value: T) -> None:
        pass
