import uuid
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field

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


class Artifact(MessagePart):
    name: str


class Message(BaseModel):
    parts: list[MessagePart]

    def __add__(self, other: "Message") -> "Message":
        if not isinstance(other, Message):
            raise TypeError(f"Cannot concatenate Message with {type(other).__name__}")
        return Message(*(self.parts + other.parts))

    def __str__(self) -> str:
        return "".join(
            part.content for part in self.parts if part.content is not None and part.content_type == "text/plain"
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


class MessageAwaitRequest(BaseModel):
    type: Literal["message"] = "message"
    message: Message


class MessageAwaitResume(BaseModel):
    type: Literal["message"] = "message"
    message: Message


AwaitRequest = Union[MessageAwaitRequest]
AwaitResume = Union[MessageAwaitResume]


class Run(BaseModel):
    run_id: RunId = Field(default_factory=uuid.uuid4)
    agent_name: AgentName
    session_id: SessionId | None = None
    status: RunStatus = RunStatus.CREATED
    await_request: AwaitRequest | None = None
    outputs: list[Message] = []
    error: Error | None = None


class MessageCreatedEvent(BaseModel):
    type: Literal["message.created"] = "message.created"
    message: Message


class MessagePartEvent(BaseModel):
    type: Literal["message.part"] = "message.part"
    part: MessagePart


class ArtifactEvent(BaseModel):
    type: Literal["message.part"] = "message.part"
    part: Artifact


class MessageCompletedEvent(BaseModel):
    type: Literal["message.completed"] = "message.completed"
    message: Message


class RunAwaitingEvent(BaseModel):
    type: Literal["run.awaiting"] = "run.awaiting"
    run: Run


class GenericEvent(BaseModel):
    type: Literal["generic"] = "generic"
    generic: AnyModel


class RunCreatedEvent(BaseModel):
    type: Literal["run.created"] = "run.created"
    run: Run


class RunInProgressEvent(BaseModel):
    type: Literal["run.in-progress"] = "run.in-progress"
    run: Run


class RunFailedEvent(BaseModel):
    type: Literal["run.failed"] = "run.failed"
    run: Run


class RunCancelledEvent(BaseModel):
    type: Literal["run.cancelled"] = "run.cancelled"
    run: Run


class RunCompletedEvent(BaseModel):
    type: Literal["run.completed"] = "run.completed"
    run: Run


Event = Union[
    RunCreatedEvent,
    RunInProgressEvent,
    MessageCreatedEvent,
    ArtifactEvent,
    MessagePartEvent,
    MessageCompletedEvent,
    RunAwaitingEvent,
    GenericEvent,
    RunCancelledEvent,
    RunFailedEvent,
    RunCompletedEvent,
    MessagePartEvent,
]


class Agent(BaseModel):
    name: str
    description: str | None = None
    metadata: Metadata = Metadata()
