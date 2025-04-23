# beeai-canvas

A simple "canvas" chat agent that can create files, iterate on documents, or write programs.

First, pull the model this example uses:

```bash
ollama pull gemma3:12b-it-qat
```

Run server with:

```python
uv run agent.py
```

...and the client with:

```python
uv run client.py
```

After generating artifacts, you will be prompted to save them to an `artifacts` subfolder.

Some prompts you may try:
- `Write a poem about bees.`
- `Create a number-guessing game in Python.`
- `For each major city in Czechia, save a file <city>.txt shortly describing it.`
