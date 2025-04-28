from collections.abc import AsyncGenerator
from datetime import datetime
from functools import reduce
from typing import TypedDict

from acp_sdk.models import Message
from acp_sdk.models.models import MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph


class AgentState(TypedDict):
    name: str
    final_response: str
    hour: int
    greeting: str


def get_current_hour(state: AgentState) -> dict[str, int]:
    now = datetime.now()
    return {"hour": now.hour}


def decide_greeting(state: AgentState) -> dict[str, str]:
    hour = state["hour"]
    if 6 <= hour < 12:
        return {"greeting": "Good morning"}
    elif 12 <= hour < 18:
        return {"greeting": "Good afternoon"}
    else:
        return {"greeting": "Good evening"}


def format_response(state: AgentState) -> dict[str, str]:
    return {"final_response": f"{state['greeting']} {state['name']}"}


# create graph
workflow = StateGraph(AgentState)

# add nodes
workflow.add_node("get_time", RunnableLambda(get_current_hour))
workflow.add_node("decide_greeting", RunnableLambda(decide_greeting))
workflow.add_node("format_response", RunnableLambda(format_response))

# connect nodes
workflow.set_entry_point("get_time")
workflow.add_edge("get_time", "decide_greeting")
workflow.add_edge("decide_greeting", "format_response")
workflow.set_finish_point("format_response")

graph = workflow.compile()

server = Server()


@server.agent()
async def lang_graph_greeting_agent(input: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """LangGraph agent that greets the user based on the current time."""
    query = reduce(lambda x, y: x + y, input)
    output = None
    async for event in graph.astream({"name": str(query)}, stream_mode="updates"):
        for value in event.items():
            yield {"update": value}
        output = event
    yield MessagePart(content=output.get("format_response", {}).get("final_response", ""))


server.run()
