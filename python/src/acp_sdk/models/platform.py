from enum import Enum
from pydantic import BaseModel, ConfigDict


class PlatformUIType(str, Enum):
    CHAT = "chat"
    HANDSOFF = "hands-off"


class PlatformUIAnnotation(BaseModel):
    ui_type: PlatformUIType
    user_greeting: str | None = None
    model_config = ConfigDict(extra="allow")
