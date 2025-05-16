from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class Store(Generic[T], ABC):
    @abstractmethod
    async def get(self, key: UUID) -> T | None:
        pass

    @abstractmethod
    async def set(self, key: UUID, value: T) -> None:
        pass

    @abstractmethod
    def watch(self, key: UUID) -> AsyncIterator[T]:
        pass

    def as_store(self, model: type[U]) -> "Store"[U]:
        return StoreView(model=model, store=self)


class StoreView(Store[U], Generic[U]):
    def __init__(self, model: type[U], store: Store[T]) -> None:
        super().__init__()
        self._model = model
        self._store = store

    async def get(self, key: UUID) -> U | None:
        value = await self._store.get(key)
        return self._model.model_validate(value.model_dump())

    async def set(self, key: UUID, value: U) -> None:
        await self._store.set(key, value)

    async def watch(self, key: UUID) -> AsyncIterator[U]:
        async for value in self._store.watch(key):
            yield self._model.model_validate(value.model_dump())
