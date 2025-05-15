from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


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
