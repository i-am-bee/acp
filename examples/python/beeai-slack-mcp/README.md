# BeeAI Slack MCP Agent

This example demonstrates how to create an Slack agent with MCP tools, through the Agent Communication Protocol (ACP).

## Overview

The Slack MCP Agent allows you to perform activities on Slack through ACP

## Prerequisites

✅ Python >= 3.11

## Installation

```bash
cp .env.sample .env
```

Edit .env to include the slack bot token and the Team ID for the workspace in which your slack app is installed.

Install the required dependencies:

```bash
# Using uv (recommended)
uv sync
```

## Usage

Start the ACP server:

```bash
uv run agent.py
```

Start the ACP client:

```bash
uv run client.py
```

## Examples

Ask:

1. Post a funny message in CXXXX slack channel
2. List the public slack channels
3. Add :tada reaction to the message in channel CXXXX with ts=1643723905.123456
