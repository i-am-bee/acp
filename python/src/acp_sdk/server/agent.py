import abc
from collections.abc import AsyncGenerator

from acp_sdk.models import (
    AgentName,
    Await,
    AwaitResume,
    Message,
    SessionId,
)
from acp_sdk.models.models import Metadata
from acp_sdk.server.context import Context


class Agent(abc.ABC):
    @property
    def name(self) -> AgentName:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return ""

    @property
    def metadata(self) -> Metadata:
        return Metadata()

    @abc.abstractmethod
    def run(self, input: Message, *, context: Context) -> AsyncGenerator[Message | Await, AwaitResume]:
        pass

    async def session(self, session_id: SessionId | None) -> SessionId | None:
        if session_id:
            raise NotImplementedError()
        return None
