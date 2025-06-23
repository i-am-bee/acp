# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
import asyncio

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
    languages: list[Language] = Field(description="List of languages to translate the text to")


class TranslationResult(BaseModel):
    text: str = Field(description="The translated text")
    language: Language = Field(description="The language of the translated text")


class TranslateToolResult(BaseModel):
    translations: list[TranslationResult] = Field(description="List of translations")


class TranslateToolOutput(ToolOutput):
    result: TranslateToolResult = Field(description="Translation result")

    def get_text_content(self) -> str:
        return to_json(self.result)

    def is_empty(self) -> bool:
        return False

    def __init__(self, result: TranslateToolResult) -> None:
        super().__init__()
        self.result = result


class TranslationTool(Tool[TranslateToolInput, ToolRunOptions, TranslateToolOutput]):
    name = "Translation"
    description = "Translate the given text to the specified languages"
    input_schema = TranslateToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "translate"],
            creator=self,
        )

    async def _run(
        self, input: TranslateToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> TranslateToolOutput:
        async def translate_to_language(lang: Language) -> TranslationResult:
            result = await run_agent(f"translation_{lang.value}", input.text)
            return TranslationResult(text=str(result[0]), language=lang)

        translations = await asyncio.gather(
            *[translate_to_language(lang) for lang in input.languages]
        )

        return TranslateToolOutput(
            result=TranslateToolResult(translations=translations)
        )
