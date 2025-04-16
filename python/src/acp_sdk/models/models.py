import uuid
from collections.abc import Iterator
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, RootModel

from acp_sdk.models.errors import Error


class Metadata(BaseModel):
    model_config = ConfigDict(extra="allow")


class AnyModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class MessagePart(BaseModel):
    name: Optional[str] = None
    content_type: str
    content: Optional[str] = None
    content_encoding: Optional[Literal["plain", "base64"]] = "plain"
    content_url: Optional[AnyUrl] = None

    model_config = ConfigDict(extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        if self.content is None and self.content_url is None:
            raise ValueError("Either content or content_url must be provided")
        if self.content is not None and self.content_url is not None:
            raise ValueError("Only one of content or content_url can be provided")


class Message(RootModel):
    root: list[MessagePart]

    def __init__(self, *items: MessagePart) -> None:
        super().__init__(root=list(items))

    def __iter__(self) -> Iterator[MessagePart]:
        return iter(self.root)

    def __add__(self, other: "Message") -> "Message":
        if not isinstance(other, Message):
            raise TypeError(f"Cannot concatenate Message with {type(other).__name__}")
        return Message(*(self.root + other.root))

    def __str__(self) -> str:
        return "".join(
            part.content for part in self.root if part.content is not None and part.content_type == "text/plain"
        )


AgentName = str
SessionId = uuid.UUID
RunId = uuid.UUID


class RunMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    STREAM = "stream"


class RunStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in-progress"
    AWAITING = "awaiting"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        terminal_states = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
        return self in terminal_states


class Await(BaseModel):
    type: Literal["placeholder"] = "placeholder"


class AwaitResume(BaseModel):
    pass


class Artifact(BaseModel):
    name: str
    content_type: str
    content: Optional[str] = None
    content_encoding: Optional[Literal["plain", "base64"]] = "plain"
    content_url: Optional[AnyUrl] = None

    model_config = ConfigDict(extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        if self.content is None and self.content_url is None:
            raise ValueError("Either content or content_url must be provided")
        if self.content is not None and self.content_url is not None:
            raise ValueError("Only one of content or content_url can be provided")


class Run(BaseModel):
    run_id: RunId = Field(default_factory=uuid.uuid4)
    agent_name: AgentName
    session_id: SessionId | None = None
    status: RunStatus = RunStatus.CREATED
    await_: Await | None = Field(None, alias="await")
    outputs: list[Message] = []
    artifacts: list[Artifact] = []
    error: Error | None = None

    model_config = ConfigDict(populate_by_name=True)

    def model_dump_json(
        self,
        **kwargs: dict[str, Any],
    ) -> str:
        return super().model_dump_json(
            by_alias=True,
            **kwargs,
        )


class MessageEvent(BaseModel):
    type: Literal["message"] = "message"
    message: Message


class ArtifactEvent(BaseModel):
    type: Literal["artifact"] = "artifact"
    artifact: Artifact


class AwaitEvent(BaseModel):
    type: Literal["await"] = "await"
    await_: Await | None = Field(alias="await")

    model_config = ConfigDict(populate_by_name=True)

    def model_dump_json(
        self,
        **kwargs: dict[str, Any],
    ) -> str:
        return super().model_dump_json(
            by_alias=True,
            **kwargs,
        )


class GenericEvent(BaseModel):
    type: Literal["generic"] = "generic"
    generic: AnyModel


class CreatedEvent(BaseModel):
    type: Literal["created"] = "created"
    run: Run


class InProgressEvent(BaseModel):
    type: Literal["in-progress"] = "in-progress"
    run: Run


class FailedEvent(BaseModel):
    type: Literal["failed"] = "failed"
    run: Run


class CancelledEvent(BaseModel):
    type: Literal["cancelled"] = "cancelled"
    run: Run


class CompletedEvent(BaseModel):
    type: Literal["completed"] = "completed"
    run: Run


RunEvent = Union[
    CreatedEvent,
    InProgressEvent,
    MessageEvent,
    AwaitEvent,
    GenericEvent,
    CancelledEvent,
    FailedEvent,
    CompletedEvent,
]


class Agent(BaseModel):
    name: str
    description: str | None = None
    metadata: Metadata = Metadata()
