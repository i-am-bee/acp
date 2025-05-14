from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Store(Generic[T], ABC):
    @abstractmethod
    async def get(self, key: str) -> T | None:
        pass

    @abstractmethod
    async def set(self, key: str, value: T) -> None:
        pass

    @abstractmethod
    def watch(self, key: str) -> AsyncIterator[T]:
        pass
