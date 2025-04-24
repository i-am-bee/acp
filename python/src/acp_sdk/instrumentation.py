from opentelemetry import trace

from acp_sdk.version import __version__


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("acp-sdk", __version__)
