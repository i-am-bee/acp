from acp_sdk import Message
from acp_sdk.client import Client
from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import ToolOutput
from beeai_framework.tools.tool import Tool
from beeai_framework.tools.types import ToolRunOptions
from beeai_framework.utils.strings import to_json
from pydantic import BaseModel, Field
from collections import defaultdict


async def run_agent(agent: str, input: list[Message]) -> list[Message]:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(agent=agent, input=input)

    return run.output


class HandoffInput(BaseModel):
    pass


class HandoffResult(BaseModel):
    result: list[Message] = Field(description="Result of the handoff")


class HandoffToolOutput(ToolOutput):
    result: HandoffResult = Field(description="Result of the handoff")

    def get_text_content(self) -> str:
        return to_json(self.result)

    def is_empty(self) -> bool:
        return self.result.result.__len__() == 0

    def __init__(self, result: HandoffResult) -> None:
        super().__init__()
        self.result = result


class HandoffTool(Tool[HandoffInput, ToolRunOptions, HandoffToolOutput]):
    def __init__(self, agent: str, session_id: str, session_storage: defaultdict[str, list[Message]]) -> None:
        self.agent = agent
        self.session_id = session_id
        self.session_storage = session_storage
        super().__init__()

    @property
    def name(self) -> str:
        return f"{self.agent}"

    @property
    def description(self) -> str:
        return f"Transfer the conversation to the {self.agent}"

    input_schema = HandoffInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "handoff"],
            creator=self,
        )

    async def _run(self, _: HandoffInput, options: ToolRunOptions | None, context: RunContext) -> HandoffToolOutput:
        history = self.session_storage.get(self.session_id)
        if history is None:
            raise ValueError("No input found for session")

        result = await run_agent(self.agent, history)
        return HandoffToolOutput(result=HandoffToolOutput(result=result))
