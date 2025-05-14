from typing import Protocol


class Stringable(Protocol):
    def __str__(self) -> str: ...
