from pydantic import BaseModel

from acp_sdk.models.models import (
    AgentManifest,
    AgentName,
    AwaitResume,
    Event,
    Message,
    Run,
    RunMode,
    Session,
    SessionId,
)


class PingResponse(BaseModel):
    pass


class AgentsListResponse(BaseModel):
    agents: list[AgentManifest]


class AgentReadResponse(AgentManifest):
    pass


class RunCreateRequest(BaseModel):
    agent_name: AgentName
    session_id: SessionId | None = None
    session: Session | None = None
    input: list[Message]
    mode: RunMode = RunMode.SYNC


class RunCreateResponse(Run):
    pass


class RunResumeRequest(BaseModel):
    await_resume: AwaitResume
    mode: RunMode


class RunResumeResponse(Run):
    pass


class RunReadResponse(Run):
    pass


class RunCancelResponse(Run):
    pass


class RunEventsListResponse(BaseModel):
    events: list[Event]


class SessionReadResponse(Session):
    pass
