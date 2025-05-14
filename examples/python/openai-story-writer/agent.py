from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel

from collections.abc import AsyncGenerator

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Server, Context
from client import run_agent


server = Server()
        
# Create an agent which can draft outline for user requested stories
@server.agent(name="story_outline_generator", description="Drafts a story outline based on user's input")
async def translation_agent(input: list[Message]) -> AsyncGenerator:
    
    story_outline_agent = Agent(
        name="story_outline_generator",
        instructions="Generate a very short story outline based on the user's input.",
        model=LitellmModel(model="ollama/mistral-small:latest", api_key="dummy", base_url="http://localhost:11434"),  # Set OPENAI_API_KEY to use OpenAI models instead
    )
    
    outline_result = await Runner.run(
        story_outline_agent,
        str(input),
    )

    yield MessagePart(content=str(outline_result.final_output))


# Create an agent to write a story along the lines of outline provided
@server.agent(name="story_writer_using_outline",description="Takes a short story outline and turns it into a story")
async def marketing_copy_agent(input: list[Message]) -> AsyncGenerator:
    
    story_agent = Agent(
        name="story_writer_using_outline",
        instructions="Write a short story based on the given outline.",
        model=LitellmModel(model="ollama/mistral-small:latest", api_key="dummy", base_url="http://localhost:11434"), # Set OPENAI_API_KEY to use OpenAI models instead
        output_type=str,
    )
    
    story_result = await Runner.run(
        story_agent,
        str(input),
    )

    yield MessagePart(content=str(story_result.final_output))


# Agent which uses story_outline_generator and story_writer_using_outline to write complete story based on user's input
@server.agent(name="story_writer",description="Generates a story using user's inputs")
async def main_agent(input: list[Message], context: Context) -> AsyncGenerator:
    
    story_outline = await run_agent("story_outline_generator", str(input))
    story = await run_agent("story_writer_using_outline", str(story_outline))

    yield MessagePart(content=str(story_outline[0]))
    yield MessagePart(content=str(story[0]))
    

if __name__ == "__main__":
    try:
        # Run the ACP server
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")