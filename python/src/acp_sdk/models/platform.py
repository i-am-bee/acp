from enum import Enum

from pydantic import BaseModel, ConfigDict


class PlatformUIType(str, Enum):
    CHAT = "chat"
    HANDSOFF = "hands-off"

class ConfigurationField(str, Enum):
    BOOLEAN = "boolean"


class AgentToolInfo(BaseModel):
    name: str
    description: str | None = None
    model_config = ConfigDict(extra="allow")


class AgentConfiguration(BaseModel):
    name: str
    description: str | None = None
    type: ConfigurationField


class PlatformUIAnnotation(BaseModel):
    ui_type: PlatformUIType
    user_greeting: str | None = None
    display_name: str | None = None
    configuration: list[AgentConfiguration] = []
    tools: list[AgentToolInfo] = []
    model_config = ConfigDict(extra="allow")
