# ACP Agent Generator Example

This example demonstrates how to create an agent that dynamically generates other agents using the Agent Communication Protocol (ACP).

## Overview

The ACP Agent Generator allows you to:
- Create new agents through natural language descriptions
- Interact with the generated agents through the standard ACP interface

## Prerequisites

✅ Python >= 3.11

## Installation

```bash 
cp .env.example .env
```

Edit .env to include atleast one API Key and Update the model and or provider if desired


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
1. Code a Agent Communctions Protocol Server that uses a BeeAI Agent to reverse the users input
2. Code a Agent Communications Protocol Agent that has access to a agent that has add and subtract tools

