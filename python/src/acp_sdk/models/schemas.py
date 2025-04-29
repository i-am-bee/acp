from pydantic import BaseModel

from acp_sdk.models.models import Agent, AgentName, AwaitResume, Event, Message, Run, RunMode, SessionId


class PingResponse(BaseModel):
    pass


class AgentsListResponse(BaseModel):
    agents: list[Agent]


class AgentReadResponse(Agent):
    pass


class RunCreateRequest(BaseModel):
    agent_name: AgentName
    session_id: SessionId | None = None
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
