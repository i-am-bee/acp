# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel

from collections.abc import AsyncGenerator

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Server, Context
from client import run_agent


server = Server()

model = LitellmModel(
    model="ollama/mistral-small:latest",
    api_key="dummy",  # Set OPENAI_API_KEY to use OpenAI models instead
    base_url="http://localhost:11434",
)


# Create an agent which can draft outline for user requested stories
@server.agent()
async def story_outline_generator(input: list[Message]) -> AsyncGenerator:
    """Drafts a story outline based on user's input"""
    story_outline_agent = Agent(
        name="story_outline_generator",
        instructions="Generate a very short story outline based on the user's input.",
        model=model,
    )

    outline_result = await Runner.run(
        story_outline_agent,
        str(input),
    )

    yield MessagePart(content=str(outline_result.final_output))


# Create an agent to write a story along the lines of outline provided
@server.agent()
async def story_writer_using_outline(input: list[Message]) -> AsyncGenerator:
    """Takes a short story outline and turns it into a story"""
    story_agent = Agent(
        name="story_writer_using_outline",
        instructions="Write a short story based on the given outline.",
        model=model,
        output_type=str,
    )

    story_result = await Runner.run(
        story_agent,
        str(input),
    )

    yield MessagePart(content=str(story_result.final_output))


# Agent which uses story_outline_generator and story_writer_using_outline to write complete story based on user's input
@server.agent()
async def story_writer(input: list[Message], context: Context) -> AsyncGenerator:
    """Generates a story using user's inputs"""
    story_outline = await run_agent("story_outline_generator", str(input))
    story = await run_agent("story_writer_using_outline", str(story_outline))

    yield MessagePart(content=str(story_outline[0]))
    yield MessagePart(content=str(story[0]))


if __name__ == "__main__":
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
