import inspect
from collections.abc import AsyncGenerator, Coroutine, Generator
from typing import Any, Callable

from acp_sdk.models import Message
from acp_sdk.server.agent import Agent
from acp_sdk.server.app import create_app
from acp_sdk.server.context import Context
from acp_sdk.server.logging import configure_logger as configure_logger_func
from acp_sdk.server.telemetry import configure_telemetry as configure_telemetry_func
from acp_sdk.server.types import RunYield, RunYieldResume


class Server:
    def __init__(self) -> None:
        self.agents: list[Agent] = []

    def agent(self, name: str | None = None, description: str | None = None) -> Callable:
        """Decorator to register an agent."""

        def decorator(fn: Callable) -> Callable:
            # check agent's function signature
            signature = inspect.signature(fn)
            parameters = list(signature.parameters.values())

            # validate agent's function
            if inspect.isasyncgenfunction(fn):
                if len(parameters) != 2:
                    raise TypeError(
                        "The agent generator function must have one 'input' argument and one 'context' argument"
                    )
            else:
                if len(parameters) != 2:
                    raise TypeError("The agent function must have one 'input' argument and one 'context' argument")

            agent: Agent
            if inspect.isasyncgenfunction(fn):

                class DecoratedAgent(Agent):
                    @property
                    def name(self) -> str:
                        return name or fn.__name__

                    @property
                    def description(self) -> str:
                        return description or fn.__doc__ or ""

                    async def run(self, input: Message, context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
                        gen: AsyncGenerator[RunYield, RunYieldResume] = fn(input, context)
                        value = None
                        while True:
                            value = yield await gen.asend(value)

                agent = DecoratedAgent()
            elif inspect.iscoroutinefunction(fn):

                class DecoratedAgent(Agent):
                    @property
                    def name(self) -> str:
                        return name or fn.__name__

                    @property
                    def description(self) -> str:
                        return description or fn.__doc__ or ""

                    async def run(self, input: Message, context: Context) -> Coroutine[RunYield]:
                        return await fn(input, context)

                agent = DecoratedAgent()
            elif inspect.isgeneratorfunction(fn):

                class DecoratedAgent(Agent):
                    @property
                    def name(self) -> str:
                        return name or fn.__name__

                    @property
                    def description(self) -> str:
                        return description or fn.__doc__ or ""

                    def run(self, input: Message, context: Context) -> Generator[RunYield, RunYieldResume]:
                        yield from fn(input, context)

                agent = DecoratedAgent()
            else:

                class DecoratedAgent(Agent):
                    @property
                    def name(self) -> str:
                        return name or fn.__name__

                    @property
                    def description(self) -> str:
                        return description or fn.__doc__ or ""

                    def run(self, input: Message, context: Context) -> RunYield:
                        return fn(input, context)

                agent = DecoratedAgent()

            self.register(agent)
            return fn

        return decorator

    def register(self, *agents: Agent) -> None:
        self.agents.extend(agents)

    def run(self, configure_logger: bool = True, configure_telemetry: bool = False, **kwargs: dict[str, Any]) -> None:
        import uvicorn

        if configure_logger:
            configure_logger_func()
        if configure_telemetry:
            configure_telemetry_func()

        uvicorn.run(create_app(*self.agents), **kwargs)
