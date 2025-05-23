import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from acp_sdk.server.store.utils import Stringable


class StoreModel(BaseModel):
    model_config = ConfigDict(extra="allow")


T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class Store(Generic[T], ABC):
    @abstractmethod
    async def get(self, key: Stringable) -> T | None:
        pass

    @abstractmethod
    async def set(self, key: Stringable, value: T | None) -> None:
        pass

    @abstractmethod
    def watch(self, key: Stringable, *, ready: asyncio.Event | None = None) -> AsyncIterator[T | None]:
        pass

    def as_store(self, model: type[U], prefix: Stringable = "") -> "Store[U]":
        return StoreView(model=model, store=self, prefix=prefix)


class StoreView(Store[U], Generic[U]):
    def __init__(self, *, model: type[U], store: Store[T], prefix: Stringable = "") -> None:
        super().__init__()
        self._model = model
        self._store = store
        self._prefix = prefix

    async def get(self, key: Stringable) -> U | None:
        value = await self._store.get(self._get_key(key))
        return self._model.model_validate(value.model_dump()) if value else value

    async def set(self, key: Stringable, value: U | None) -> None:
        await self._store.set(self._get_key(key), value)

    async def watch(self, key: Stringable, *, ready: asyncio.Event | None = None) -> AsyncIterator[U | None]:
        async for value in self._store.watch(self._get_key(key), ready=ready):
            yield self._model.model_validate(value.model_dump()) if value else value

    def _get_key(self, key: Stringable) -> str:
        return f"{self._prefix!s}{key!s}"
