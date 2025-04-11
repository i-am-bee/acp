from typing import Any

from acp_sdk.models import Await, AwaitResume, Message

RunYield = Message | Await | dict[str | Any]
RunYieldResume = AwaitResume | None
