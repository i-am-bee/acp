import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from acp_sdk.models import Message, MessagePart
from acp_sdk.models.errors import ACPError, Error, ErrorCode
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from gpt_researcher import GPTResearcher

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
logger = logging.getLogger(__name__)


@server.agent()
async def gpt_researcher(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    parts = [part for message in input for part in message.parts]
    if len(parts) != 1:
        raise ACPError(Error(code=ErrorCode.INVALID_INPUT, message="Please provide exactly one query."))
    query = parts[0].content

    class CustomLogsHandler:
        async def send_json(self, data: dict[str, Any]) -> None:
            match data.get("type"):
                case "logs":
                    log_output = data.get("output", "")
                    await context.yield_async(
                        Message(parts=[MessagePart(content_type="text/plain", content=log_output)])
                    )
                case "report":
                    report_output = data.get("output", "")
                    await context.yield_async(
                        Message(parts=[MessagePart(content_type="text/plain", content=report_output)])
                    )
                case _:  # handle other types of logs
                    generic_output = f"Unhandled log type {data.get('type')}: {data.get('output', '')}"
                    await context.yield_async(
                        Message(parts=[MessagePart(content_type="text/plain", content=generic_output)])
                    )

    handler = CustomLogsHandler()
    researcher = GPTResearcher(query=query, report_type="research_report", websocket=handler)
    await researcher.conduct_research()
    report_output = await researcher.write_report()
    yield Message(parts=[MessagePart(content_type="text/plain", content=report_output)])


if __name__ == "__main__":
    server.run()
