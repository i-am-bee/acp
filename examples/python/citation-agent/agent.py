from collections.abc import AsyncGenerator

from acp_sdk import Message, Metadata
from acp_sdk.models import MessagePart
from acp_sdk.models.models import Annotations, CitationMetadata
from acp_sdk.models.platform import PlatformUIAnnotation, PlatformUIType
from acp_sdk.server import Context, Server

server = Server()


@server.agent(
    metadata=Metadata(
        annotations=Annotations(
            beeai_ui=PlatformUIAnnotation(ui_type=PlatformUIType.CHAT, user_greeting="Let's test citations")
        )
    )
)
async def citation_agent(input: list[Message], context: Context) -> AsyncGenerator:
    yield MessagePart(
        content="If you are bored, you can try tipping a cow.",
    )
    yield MessagePart(
        metadata=CitationMetadata(url="https://en.wikipedia.org/wiki/Cow_tipping", start_index=30, end_index=43)
    )


server.run()
