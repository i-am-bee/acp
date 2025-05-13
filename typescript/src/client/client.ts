import { ErrorModel } from "../models/errors.js";
import { Agent, AgentName, AwaitResume, Event, Run, RunId, RunMode } from "../models/models.js";
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
}

export class Client {
  #baseUrl: string;
  #fetch: FetchLike;

  constructor(init?: ClientInit) {
    this.#fetch = init?.fetch ?? globalThis.fetch;
    this.#baseUrl = normalizeBaseUrl(init?.baseUrl ?? '');
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
    const data = await this.#fetcher("/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(RunCreateRequest.parse({
        agent_name: agentName,
        input: inputToMessages(input),
        mode: RunMode.enum.sync,
      })),
    });
    return RunCreateResponse.parse(data);
  }

  async runAsync(agentName: AgentName, input: Input): Promise<Run> {
    const data = await this.#fetcher("/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(RunCreateRequest.parse({
        agent_name: agentName,
        input: inputToMessages(input),
        mode: RunMode.enum.async,
      })),
    });
    return RunCreateResponse.parse(data);
  }

  async runStatus(runId: RunId): Promise<Run> {
    const data = await this.#fetcher(`/runs/${runId}`, { method: 'GET' });
    return RunReadResponse.parse(data);
  }

  async runEvents(runId: RunId): Promise<Event[]> {
    const data = await this.#fetcher(`/runs/${runId}/events`, { method: 'GET' });
    return RunEventsListResponse.parse(data).events;
  }

  async runCancel(runId: RunId): Promise<Run> {
    const data = await this.#fetcher(`/runs/${runId}/cancel`, { method: 'POST' });
    return RunReadResponse.parse(data);
  }

  async runResumeSync(runId: RunId, awaitResume: AwaitResume): Promise<Run> {
    const data = await this.#fetcher(`/runs/${runId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(RunResumeRequest.parse({
        await_resume: awaitResume,
        mode: RunMode.enum.sync,
      })),
    });
    return RunResumeResponse.parse(data);
  }

  async runResumeAsync(runId: RunId, awaitResume: AwaitResume): Promise<Run> {
    const data = await this.#fetcher(`/runs/${runId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(RunResumeRequest.parse({
        await_resume: awaitResume,
        mode: RunMode.enum.async,
      })),
    });
    return RunResumeResponse.parse(data);
  }
}

const normalizeBaseUrl = (url: string) => {
  if (url.endsWith('/')) {
    return url.slice(0, -1);
  }
  return url;
}
