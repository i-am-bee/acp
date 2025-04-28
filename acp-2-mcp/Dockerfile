FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY . .

RUN uv sync

CMD ["uv", "run", "python", "server.py", "${ACP_URL}"]
