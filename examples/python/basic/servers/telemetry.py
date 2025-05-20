import logging
from collections.abc import AsyncGenerator
from random import choice

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server()


@server.agent()
async def random(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Random"""

    logger.info("Generating random answer ...")
    yield f"The answer is {choice(['YES', 'NO'])}"
    logger.info("Generation finished")


server.run(configure_telemetry=True)  # Export traces, metrics and logs to OTEL backend via OTLP protocol.

# Start any OTEL backend before running, e.g. https://github.com/ymtdzzz/otel-tui
