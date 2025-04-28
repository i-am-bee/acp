from enum import Enum

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



class Language(str, Enum):
    spanish = "spanish"
    french = "french"


class TranslateToolInput(BaseModel):
    text: str = Field(description="The text to translate")
    language: Language = Field(description="The language to translate the text to")


class TranslateToolResult(BaseModel):
    text: str = Field(description="The translated text")


class TranslateToolOutput(ToolOutput):
    result: TranslateToolResult = Field(description="Translation result")

    def get_text_content(self) -> str:
        return to_json(self.result)

    def is_empty(self) -> bool:
        return self.result.text == ""

    def __init__(self, result: TranslateToolResult) -> None:
        super().__init__()
        self.result = result


class TranslationTool(Tool[TranslateToolInput, ToolRunOptions, TranslateToolOutput]):
    name = "Translation"
    description = "Translate the given text to the specified language"
    input_schema = TranslateToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "translate"],
            creator=self,
        )

    async def _run(
        self, input: TranslateToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> TranslateToolOutput:
        if input.language == Language.spanish:
            result = await run_agent("translation_spanish", input.text)
        elif input.language == Language.french:
            result = await run_agent("translation_french", input.text)

        return TranslateToolOutput(result=TranslateToolResult(text=str(result[0])))
