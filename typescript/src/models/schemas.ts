import * as z from "zod";
import {
  AgentManifest,
  AgentName,
  AwaitResume,
  Event,
  Message,
  Run,
  RunMode,
  SessionId,
} from "./models.js";

export const PingResponse = z.object({});

export const AgentsListResponse = z.object({
  agents: z.array(AgentManifest),
});

export const AgentsReadResponse = AgentManifest;

export const RunCreateRequest = z.object({
  agent_name: AgentName,
  session_id: z.optional(SessionId),
  input: z.array(Message),
  mode: RunMode,
});

export type RunCreateRequest = z.infer<typeof RunCreateRequest>;

export const RunCreateResponse = Run;

export const RunEventsListResponse = z.object({
  events: z.array(Event),
});

export const RunResumeRequest = z.object({
  await_resume: AwaitResume,
  mode: RunMode,
})

export type RunResumeRequest = z.infer<typeof RunResumeRequest>;

export const RunResumeResponse = Run;

export const RunReadResponse = Run;

