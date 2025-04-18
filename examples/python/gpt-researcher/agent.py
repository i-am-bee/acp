import os
import asyncio
from typing import AsyncGenerator, Any, Awaitable
from gpt_researcher import GPTResearcher
from acp_sdk.models import Message, MessagePart
from acp_sdk.models.errors import Error, ACPError, ErrorCode
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

os.environ.update(
    {
        "RETRIEVER": "duckduckgo",
        "OPENAI_BASE_URL": "http://localhost:11434/v1",
        "OPENAI_API_KEY": "dummy",
        "FAST_LLM": "openai:llama3.1",
        "SMART_LLM": "openai:llama3.1",
        "STRATEGIC_LLM": "openai:llama3.1",
    }
)

server = Server()


async def enqueue_message(queue: asyncio.Queue, content: str):
    await queue.put(
        Message(parts=[MessagePart(content_type="text/plain", content=content)])
    )


class CustomLogsHandler:
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def send_json(self, data: dict[str, Any]) -> None:
        match data.get("type"):
            case "logs":
                log_output = data.get("output", "")
                await enqueue_message(self.queue, log_output)
            case "report":
                report_output = data.get("output", "")
                await enqueue_message(self.queue, report_output)
            case _:  # handle other types of logs
                generic_output = (
                    f"Unhandled log type {data.get('type')}: {data.get('output', '')}"
                )
                await enqueue_message(self.queue, generic_output)


async def perform_research(query: str, queue: asyncio.Queue):
    handler = CustomLogsHandler(queue)
    researcher = GPTResearcher(
        query=query, report_type="research_report", websocket=handler
    )

    await researcher.conduct_research()
    report = await researcher.write_report()
    await enqueue_message(queue, report)
    await queue.put(None)


@server.agent()
async def gpt_researcher(
    input: Message, context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:

    if len(input) != 1:
        raise ACPError(
            Error(
                code=ErrorCode.INVALID_INPUT,
                message="Please provide exactly one query.",
            )
        )

    message_queue = asyncio.Queue()

    research_task = asyncio.create_task(perform_research(input[0], message_queue))

    while True:
        msg = await message_queue.get()
        if msg is None:
            break
        yield msg

    await research_task


server.run()
