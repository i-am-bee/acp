from enum import Enum
from typing import Annotated, Literal, Union
import uuid

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, RootModel


class ACPError(BaseModel):
    code: str
    message: str


class AnyModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class MessagePartBase(BaseModel):
    type: Literal["text", "image", "artifact"]


class TextMessagePart(MessagePartBase):
    type: Literal["text"] = "text"
    content: str


class ImageMessagePart(MessagePartBase):
    type: Literal["image"] = "image"
    content_url: AnyUrl


class ArtifactMessagePart(MessagePartBase):
    type: Literal["artifact"] = "artifact"
    name: str
    content_url: AnyUrl


MessagePart = Union[TextMessagePart, ImageMessagePart, ArtifactMessagePart]


class Message(RootModel):
    root: list[MessagePart]

    def __init__(self, *items: MessagePart):
        super().__init__(root=list(items))

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __add__(self, other: "Message") -> "Message":
        if not isinstance(other, Message):
            raise TypeError(f"Cannot concatenate Message with {type(other).__name__}")
        return Message(*(self.root + other.root))

    def __str__(self):
        return "".join(
            str(part) for part in self.root if isinstance(part, TextMessagePart)
        )


AgentName = str
SessionId = str
RunId = str


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


class Run(BaseModel):
    run_id: RunId = str(uuid.uuid4())
    agent_name: AgentName
    session_id: SessionId | None = None
    status: RunStatus = RunStatus.CREATED
    await_: Await | None = Field(None, alias="await")
    output: Message | None = None
    error: ACPError | None = None

    model_config = ConfigDict(populate_by_name=True)

    def model_dump_json(
        self,
        **kwargs,
    ):
        return super().model_dump_json(
            by_alias=True,
            **kwargs,
        )


class MessageEvent(BaseModel):
    type: Literal["message"] = "message"
    message: Message


class AwaitEvent(BaseModel):
    type: Literal["await"] = "await"
    await_: Await | None = Field(alias="await")

    model_config = ConfigDict(populate_by_name=True)

    def model_dump_json(
        self,
        **kwargs,
    ):
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


class RunCreateRequest(BaseModel):
    agent_name: AgentName
    session_id: SessionId | None = None
    input: Message
    mode: RunMode = RunMode.SYNC


class RunCreateResponse(Run):
    pass


class RunResumeRequest(BaseModel):
    await_: AwaitResume = Field(alias="await")
    mode: RunMode


class RunResumeResponse(Run):
    pass


class RunReadResponse(Run):
    pass


class RunCancelResponse(Run):
    pass


class Agent(BaseModel):
    name: str
    description: str | None = None


class AgentsListResponse(BaseModel):
    agents: list[Agent]


class AgentReadResponse(Agent):
    pass
