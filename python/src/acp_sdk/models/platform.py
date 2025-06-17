from enum import Enum

from pydantic import BaseModel


class PlatformAnnotationType(str, Enum):
    UI_TYPE = "ui-type"


class PlatformUIType(str, Enum):
    CHAT = ("chat",)
    HANDSOFF = "hands-off"


class PlatformAnnotation(BaseModel):
    type: PlatformAnnotationType


class PlatformUIAnnotation(PlatformAnnotation):
    type: PlatformAnnotationType.UI_TYPE
    ui_type: PlatformUIType
    user_greeting: str | None = None


class PlatformAnnotations(BaseModel):
    beeai_platform: list[PlatformUIAnnotation] = []
