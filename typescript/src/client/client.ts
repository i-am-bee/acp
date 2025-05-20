import { v4 as uuuid } from "uuid";
import { ErrorModel } from "../models/errors.js";
import {
  Agent,
  AgentName,
  AwaitResume,
  Event,
  Run,
  RunId,
  SessionId,
} from "../models/models.js";
import {
  AgentsListResponse,
  AgentsReadResponse,
  PingResponse,
  RunCreateRequest,
  RunCreateResponse,
  RunEventsListResponse,
  RunReadResponse,
  RunResumeRequest,
  RunResumeResponse,
} from "../models/schemas.js";
import { ACPError, BaseError, FetchError, HTTPError } from "./errors.js";
import { createEventSource, EventSource } from "./sse.js";
import { Input } from "./types.js";
import { inputToMessages } from "./utils.js";

type FetchLike = typeof fetch;

interface ClientInit {
  baseUrl?: string;
  /**
   * Optional fetch implementation to use. Defaults to `globalThis.fetch`.
   * Can also be used for advanced use cases like mocking, proxying, custom certs etc.
   */
  fetch?: FetchLike;
  sessionId?: string;
}

export class Client {
  #baseUrl: string;
  #fetch: FetchLike;
  #sessionId?: SessionId;

  constructor(init?: ClientInit) {
    this.#fetch = init?.fetch ?? globalThis.fetch;
    this.#baseUrl = normalizeBaseUrl(init?.baseUrl ?? "");
    this.#sessionId = init?.sessionId;
  }

  get sessionId() {
    return this.#sessionId;
  }

  async withSession(
    cb: (session: Client) => Promise<void>,
    sessionId: SessionId = uuuid()
  ) {
    const client = new Client({
      fetch: this.#fetch,
      baseUrl: this.#baseUrl,
      sessionId,
    });
    return await cb(client);
  }

  async #fetcher(url: string, options?: RequestInit) {
    let response: Response | undefined;
    try {
      response = await this.#fetch(this.#baseUrl + url, options);
      await this.#handleErrorResponse(response);
      return await response.json();
    } catch (err) {
      if (
        err instanceof BaseError ||
        (err instanceof Error && err.name === "AbortError")
      ) {
        throw err;
      }
      throw new FetchError((err as Error).message ?? "fetch failed", response, {
        cause: err,
      });
    }
  }

  async #fetchEventSource(url: string, options?: RequestInit) {
    let eventSource: EventSource;
    try {
      eventSource = await createEventSource({
        url: this.#baseUrl + url,
        fetch: this.#fetch,
        options,
      });
    } catch (err) {
      throw new FetchError(
        (err as Error).message ?? "fetch failed",
        undefined,
        {
          cause: err,
        }
      );
    }
    await this.#handleErrorResponse(eventSource.response);
    return eventSource;
  }

  async #handleErrorResponse(response: Response) {
    if (response.ok) return;

    const text = await response.text();
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      throw new HTTPError(response, text);
    }

    const result = ErrorModel.safeParse(data);
    if (result.success) {
      throw new ACPError(result.data);
    }
    throw new HTTPError(response, data);
  }

  async *#processEventSource(eventSource: EventSource) {
    for await (const message of eventSource.consume()) {
      const event = Event.parse(JSON.parse(message.data));
      if (event.type === "error") {
        throw new ACPError(event.error);
      }
      yield event;
    }
  }

  async ping() {
    const data = await this.#fetcher("/ping", { method: "GET" });
    PingResponse.parse(data);
  }

  async agents(): Promise<Agent[]> {
    const data = await this.#fetcher("/agents", { method: "GET" });
    return AgentsListResponse.parse(data).agents;
  }

  async agent(name: AgentName): Promise<Agent> {
    const data = await this.#fetcher(`/agents/${name}`, { method: "GET" });
    return AgentsReadResponse.parse(data);
  }

  async runSync(agentName: AgentName, input: Input): Promise<Run> {
    const data = await this.#fetcher(
      "/runs",
      jsonPost<RunCreateRequest>({
        agent_name: agentName,
        input: inputToMessages(input),
        mode: "sync",
        session_id: this.#sessionId,
      })
    );
    return RunCreateResponse.parse(data);
  }

  async runAsync(agentName: AgentName, input: Input): Promise<Run> {
    const data = await this.#fetcher(
      "/runs",
      jsonPost<RunCreateRequest>({
        agent_name: agentName,
        input: inputToMessages(input),
        mode: "async",
        session_id: this.#sessionId,
      })
    );
    return RunCreateResponse.parse(data);
  }

  async *runStream(
    agentName: AgentName,
    input: Input
  ): AsyncGenerator<Event, void, unknown> {
    const eventSource = await this.#fetchEventSource(
      "/runs",
      jsonPost<RunCreateRequest>({
        agent_name: agentName,
        input: inputToMessages(input),
        mode: "stream",
        session_id: this.#sessionId,
      })
    );
    for await (const event of this.#processEventSource(eventSource)) {
      yield event;
    }
  }

  async runStatus(runId: RunId): Promise<Run> {
    const data = await this.#fetcher(`/runs/${runId}`, { method: "GET" });
    return RunReadResponse.parse(data);
  }

  async runEvents(runId: RunId): Promise<Event[]> {
    const data = await this.#fetcher(`/runs/${runId}/events`, {
      method: "GET",
    });
    return RunEventsListResponse.parse(data).events;
  }

  async runCancel(runId: RunId): Promise<Run> {
    const data = await this.#fetcher(`/runs/${runId}/cancel`, {
      method: "POST",
    });
    return RunReadResponse.parse(data);
  }

  async runResumeSync(runId: RunId, awaitResume: AwaitResume): Promise<Run> {
    const data = await this.#fetcher(
      `/runs/${runId}`,
      jsonPost<RunResumeRequest>({
        await_resume: awaitResume,
        mode: "sync",
      })
    );
    return RunResumeResponse.parse(data);
  }

  async runResumeAsync(runId: RunId, awaitResume: AwaitResume): Promise<Run> {
    const data = await this.#fetcher(
      `/runs/${runId}`,
      jsonPost<RunResumeRequest>({
        await_resume: awaitResume,
        mode: "async",
      })
    );
    return RunResumeResponse.parse(data);
  }

  async *runResumeStream(
    runId: RunId,
    awaitResume: AwaitResume
  ): AsyncGenerator<Event, void, unknown> {
    const eventSource = await this.#fetchEventSource(
      `/runs/${runId}`,
      jsonPost<RunResumeRequest>({
        await_resume: awaitResume,
        mode: "stream",
      })
    );
    for await (const event of this.#processEventSource(eventSource)) {
      yield event;
    }
  }
}

const normalizeBaseUrl = (url: string) => {
  if (url.endsWith("/")) {
    return url.slice(0, -1);
  }
  return url;
};

const jsonPost = <T>(json: T): RequestInit => {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(json),
  };
};
