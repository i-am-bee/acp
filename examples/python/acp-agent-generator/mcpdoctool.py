# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from mcpdoc.main import create_server

# This is a simple example of how to use the mcpdoc library to create a server
# that serves documentation sources for the Agent Communication Protocol (ACP) and Langraph.
if __name__ == "__main__":
    # Create a server with documentation sources
    server = create_server(
        [
            {
                "name": "Agent Communication Protocol Documentation",
                "llms_txt": "https://agentcommunicationprotocol.dev/llms.txt",  # Can't use llms_full.txt otherwise it will hit the rate limit
            },
            {
                "name": "Langraph Documentation",
                "llms_txt": "https://langchain-ai.github.io/langgraph/llms.txt",
            },
            {
                "name": "BeeAI Documentation",
                "llms_txt": "https://docs.beeai.dev/llms.txt",  # Can't use llms_full.txt otherwise it will hit the rate limit
            },
            # You can add multiple documentation sources
            # {
            #     "name": "Another Documentation",
            #     "llms_txt": "https://example.com/llms.txt",
            # },
        ],
        follow_redirects=True,
        timeout=15.0,
        allowed_domains=["*"],
    )

    # Run the server
    server.run(transport="stdio")
