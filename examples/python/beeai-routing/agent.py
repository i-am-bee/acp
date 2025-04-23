from collections.abc import AsyncGenerator

from pydantic import BaseModel, Field
from enum import Enum

from acp_sdk import Message
from acp_sdk.client import Client
from acp_sdk.models import MessagePart
from acp_sdk.server import Context, Server
from beeai_framework.backend.chat import ChatModel
from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory import TokenMemory
from beeai_framework.tools.tool import Tool
from beeai_framework.tools.types import ToolRunOptions
from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import ToolOutput
from beeai_framework.utils.strings import to_json
from beeai_framework.utils.dicts import exclude_none

server = Server()

async def run_agent(agent: str, input: str) -> list[Message]:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent=agent, inputs=[Message(parts=[MessagePart(content=input, content_type="text/plain")])]
        )

    return run

class Language(str, Enum):
    spanish = 'spanish'
    french = 'french'
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

@server.agent(name="translation_spanish")
async def translation_spanish_agent(inputs: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(prompt="Translate the given text to Spanish. The text is: " + str(inputs))

    yield MessagePart(content=response.result.text)

@server.agent(name="translation_french")
async def translation_french_agent(inputs: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(prompt="Translate the given text to French. The text is: " + str(inputs))

    yield MessagePart(content=response.result.text)

class TranslationTool(Tool[TranslateToolInput, ToolRunOptions, TranslateToolOutput]):
    name = "Translation"
    description = "Translate the given text to the specified language"
    input_schema = TranslateToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "translate"],
            creator=self,
        )


    async def _run(self, input: TranslateToolInput, options: ToolRunOptions | None, context: RunContext) -> TranslateToolOutput:
        if input.language == Language.spanish:
            result = await run_agent("translation_spanish", input.text)
        elif input.language == Language.french:
            result = await run_agent("translation_french", input.text)

        return TranslateToolOutput(result=TranslateToolResult(text=str(result[0])))


@server.agent(name="router")
async def main_agent(inputs: list[Message], context: Context) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")
    
    agent = ReActAgent(
        llm=llm,
        tools=[TranslationTool()],
        templates={
            "system": lambda template: template.update(
                defaults=exclude_none({"instructions": "Translate the given text to either Spanish or French using the translation tool. Return only the result from the tool as it is, don't change it.", "role": "system"})
            )
        },
        memory=TokenMemory(llm)
    )

    prompt = (str(inputs[0]))
    response = await agent.run(prompt)


    yield MessagePart(content=response.result.text)


server.run()
