from pydantic import BaseModel, ConfigDict, Field

from acp_sdk.models.models import Agent, AgentName, AwaitResume, Message, Run, RunMode, SessionId


class AgentsListResponse(BaseModel):
    agents: list[Agent]


class AgentReadResponse(Agent):
    pass


class RunCreateRequest(BaseModel):
    agent_name: AgentName
    session_id: SessionId | None = None
    inputs: list[Message]
    mode: RunMode = RunMode.SYNC


class RunCreateResponse(Run):
    pass


class RunResumeRequest(BaseModel):
    await_: AwaitResume = Field(alias="await")
    mode: RunMode

    model_config = ConfigDict(populate_by_name=True)


class RunResumeResponse(Run):
    pass


class RunReadResponse(Run):
    pass


class RunCancelResponse(Run):
    pass
