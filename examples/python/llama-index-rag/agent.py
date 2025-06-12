## Reference: https://medium.com/mitb-for-all/a-guide-to-code-testing-rag-agents-without-real-llms-or-vector-dbs-51154ad920be
from collections.abc import AsyncGenerator

from acp_sdk import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server

from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.agent.workflow import FunctionAgent, AgentStream
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.readers.docling import DoclingReader
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

## Load document
reader = DoclingReader()
node_parser = MarkdownNodeParser()
documents = reader.load_data("https://arxiv.org/pdf/2408.09869")

## Create RAG query engine
# Settings.llm = OpenAI("gpt-4o-mini", temperature=0)
# Settings.embed_model = OpenAIEmbeddings()

Settings.llm = Ollama("qwen2.5", temperature=0)
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")

index = VectorStoreIndex.from_documents(
    documents=documents,
    transformations=[node_parser]
)
query_engine = index.as_query_engine()

## Create the agent
tools = [
    QueryEngineTool(
        query_engine = query_engine,
        metadata = ToolMetadata(
            name="Docling_Knowledge_Base",
            description="Use this tool to answer any questions related to the Docling framework"
        )
    )
]
agent = FunctionAgent(tools=tools, llm=Settings.llm)

server = Server()

@server.agent()
async def llamaindex_rag_agent(input: list[Message]) -> AsyncGenerator:
    """LlamaIndex agent that answers questions using the  Docling
    knowledge base. The agent answers questions in streaming mode."""

    query = str(input[-1])
    handler = agent.run(query)
    async for ev in handler.stream_events():
        if isinstance(ev, AgentStream):
            yield ev.delta
    response = await handler
    yield str(response)

if __name__ == "__main__":
    server.run()
