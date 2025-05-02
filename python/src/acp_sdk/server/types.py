from typing import Any

from pydantic import BaseModel

from acp_sdk.models import AwaitRequest, AwaitResume, Message
from acp_sdk.models.models import MessagePart

RunYield = Message | MessagePart | str | AwaitRequest | BaseModel | dict[str | Any] | None | Exception
RunYieldResume = AwaitResume | None
