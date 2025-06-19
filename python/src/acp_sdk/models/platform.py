from enum import Enum

from pydantic import BaseModel, ConfigDict


class PlatformUIType(str, Enum):
    CHAT = "chat"
    HANDSOFF = "hands-off"


class AgentToolInfo(BaseModel):
    name: str
    description: str | None = None
    model_config = ConfigDict(extra="allow")


class PlatformUIAnnotation(BaseModel):
    ui_type: PlatformUIType
    user_greeting: str | None = None
    display_name: str | None = None
    tools: list[AgentToolInfo] = []
    model_config = ConfigDict(extra="allow")
