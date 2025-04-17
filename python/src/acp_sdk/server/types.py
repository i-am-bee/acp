from typing import Any

from acp_sdk.models import AwaitRequest, AwaitResume, Message

RunYield = Message | AwaitRequest | dict[str | Any]
RunYieldResume = AwaitResume | None
