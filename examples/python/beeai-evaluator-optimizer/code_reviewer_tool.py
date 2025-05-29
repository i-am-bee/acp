from acp_sdk import Message
from acp_sdk.client import Client
from acp_sdk.models import MessagePart
from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import ToolOutput
from beeai_framework.tools.tool import Tool
from beeai_framework.tools.types import ToolRunOptions
from beeai_framework.utils.strings import to_json
from pydantic import BaseModel, Field


async def run_agent(agent: str, input: str) -> list[Message]:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent=agent, input=[Message(parts=[MessagePart(content=input, content_type="text/plain")])]
        )

    return run.output


class CodeReviewerToolInput(BaseModel):
    code: str = Field(description="Code to be reviewed")


class CodeReviwerToolResult(BaseModel):
    suggestions: str = Field(description="Suggestions for code improvement")


class CodeReviwerToolOutput(ToolOutput):
    result: CodeReviwerToolResult = Field(description="Code review result")

    def get_text_content(self) -> str:
        return to_json(self.result)

    def is_empty(self) -> bool:
        return False

    def __init__(self, result: CodeReviwerToolResult) -> None:
        super().__init__()
        self.result = result


class CodeReviewerTool(Tool[CodeReviewerToolInput, ToolRunOptions, CodeReviwerToolOutput]):
    name = "Code Reviewer"
    description = "Reviews the given code and provides suggestions for improvement"
    input_schema = CodeReviewerToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "code_review"],
            creator=self,
        )

    async def _run(
        self, input: CodeReviewerToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> CodeReviwerToolOutput:
        result = await run_agent("code_reviewer", input.code)

        return CodeReviwerToolOutput(result=CodeReviwerToolResult(suggestions=str(result[0])))
