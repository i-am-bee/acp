import { EventSourceParserStream } from "eventsource-parser/stream";
import { SSEError } from "./errors.js";

type FetchLike = typeof fetch;

interface EventSourceParams {
  url: URL | string;
  fetch?: FetchLike;
  options?: RequestInit;
}

export async function createEventSource({
  url,
  fetch = globalThis.fetch,
  options,
}: EventSourceParams) {
  const response = await fetch(url, getFetchOptions(options));
  return {
    response,
    async *consume() {
      if (response.status === 204) {
        throw new SSEError("Server sent HTTP 204, not connecting", response);
      }

      if (!response.ok) {
        throw new SSEError(
          `Non-200 status code (${response.status})`,
          response
        );
      }

      if (
        !response.headers.get("content-type")?.startsWith("text/event-stream")
      ) {
        throw new SSEError(
          'Invalid content type, expected "text/event-stream"',
          response
        );
      }

      if (!response.body) {
        throw new SSEError("Missing response body", response);
      }

      const stream = response.body
        .pipeThrough(new TextDecoderStream())
        .pipeThrough(new EventSourceParserStream({ onError: "terminate" }));

      try {
        for await (const message of stream) {
          yield message;
        }
      } catch (e) {
        const err = e as Error;
        if (err.name !== 'AbortError') {
          throw new SSEError(err.message, response, { cause: err });
        } else {
          throw err;
        }
      }
    },
  };
}

export type EventSource = Awaited<ReturnType<typeof createEventSource>>;

export type { EventSourceMessage } from 'eventsource-parser';

function getFetchOptions(options?: RequestInit): RequestInit {
  return {
    ...options,
    headers: { Accept: "text/event-stream", ...options?.headers },
    cache: "no-store",
  };
}
