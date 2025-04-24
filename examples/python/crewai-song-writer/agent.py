from collections.abc import Iterator
from typing import Any

from acp_sdk import Message, MessagePart
from acp_sdk.server import Context, Server
from crewai import LLM, Agent, Crew, Task
from crewai.agents.parser import AgentAction, AgentFinish
from crewai_tools import ScrapeWebsiteTool
from pydantic import AnyUrl

llm = LLM(model="openai/llama3.1", base_url="http://localhost:11434/v1", api_key="dummy")

server = Server()


@server.agent()
def song_writer_agent(inputs: list[Message], context: Context) -> Iterator:
    """Agent that writes a song about a website. Accepts a message with URL"""

    try:
        url = str(AnyUrl(str(inputs[-1])))
    except ValueError:
        yield MessagePart(content="This is not a URL, please provide valid website.")
        return

    website_scraper = Agent(
        llm=llm,
        role="Website Researcher",
        goal="Find useful content for songwriting from this website: {url}",
        backstory="Expert researcher who finds inspiring stories and themes online.",
        verbose=True,
        tools=[ScrapeWebsiteTool()],
    )

    song_writer = Agent(
        llm=llm,
        role="Songwriter",
        goal="Create songs from research material.",
        backstory="Talented songwriter who transforms information into emotional, memorable songs.",
        verbose=True,
    )

    scrape_task = Task(
        description="Research this URL for songwriting material: {url}",
        expected_output="Collection of themes, stories, and facts for songwriting inspiration.",
        agent=website_scraper,
    )

    write_song_task = Task(
        description="Write a song based on research.",
        expected_output="Complete song with lyrics and style based on research.",
        agent=song_writer,
    )

    def step_callback(event: Any, *args, **kwargs) -> None:
        match event:
            case AgentAction():
                context.yield_sync(
                    {
                        "thought": event.thought,
                        "tool": event.tool,
                        "tool_input": event.tool_input,
                        "result": event.result,
                    }
                )
            case AgentFinish():
                context.yield_sync({"output": event.output})
            case _:
                return  # unsupported event

    crew = Crew(
        agents=[website_scraper, song_writer],
        tasks=[scrape_task, write_song_task],
        verbose=True,
        step_callback=step_callback,
    )
    result = crew.kickoff(inputs={"url": url})
    yield MessagePart(content=result.raw)


if __name__ == "__main__":
    server.run()
