import * as z from "zod";
import { Simplify } from 'type-fest';
import { ErrorModel } from "./errors.js";
import { createSchemaTypePredicate } from "./utils.js";

export const AnyModel = z.record(z.any());

export const Author = z.object({
  name: z.string(),
  email: z.string().optional(),
  url: z.string().url().optional(),
});

export const Contributor = z.object({
  name: z.string(),
  email: z.string().optional(),
  url: z.string().url().optional(),
});

export const LinkType = z.enum([
  "source-code",
  "container-image",
  "homepage",
  "documentation",
]);

export const Link = z.object({
  type: LinkType,
  url: z.string().url(),
});

export const DependencyType = z.enum(["agent", "tool", "model"]);

export const Dependency = z.object({
  type: DependencyType,
  name: z.string(),
});

export const Capability = z.object({
  name: z.string(),
  description: z.string(),
});

export const Metadata = z
  .object({
    annotations: AnyModel,
    documentation: z.string(),
    license: z.string(),
    programming_language: z.string(),
    natural_languages: z.array(z.string()),
    framework: z.string(),
    capabilities: z.array(Capability),
    domains: z.array(z.string()),
    tags: z.array(z.string()),
    created_at: z.string().datetime(),
    updated_at: z.string().datetime(),
    author: Author,
    contributors: z.array(Contributor),
    links: z.array(Link),
    dependencies: z.array(Dependency),
    recommended_models: z.array(z.string()),
  })
  .partial()
  .passthrough();

const BaseMessagePart = z
  .object({
    name: z.string(),
    content_type: z.string().default("text/plain"),
    content: z.string(),
    content_encoding: z.enum(["plain", "base64"]).default("plain"),
    content_url: z.string().url(),
  })
  .partial()
  .passthrough();

const refineMessagePart = (
  val: z.infer<typeof BaseMessagePart>,
  ctx: z.RefinementCtx
) => {
  if (val.content == null && val.content_url == null) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Either content or content_url must be provided",
    });
  } else if (val.content != null && val.content_url != null) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Only one of content or content_url can be provided",
    });
  }
  return z.NEVER;
};

export const MessagePart = BaseMessagePart.superRefine(refineMessagePart);

export type MessagePart = Simplify<z.infer<typeof MessagePart>>;

export const isMessagePart = createSchemaTypePredicate(MessagePart);

export const Artifact = BaseMessagePart.required({ name: true }).superRefine(
  refineMessagePart
);

// TODO: there are methods to be implemented
export const Message = z.object({
  parts: z.array(MessagePart),
  created_at: z
    .string()
    .datetime()
    .default(() => new Date().toISOString()),
  completed_at: z
    .string()
    .datetime()
    .default(() => new Date().toISOString()),
});

export type Message = z.infer<typeof Message>;

export const isMessage = createSchemaTypePredicate(Message);

const UUID = z.string().uuid();

export const AgentName = z.string();

export type AgentName = z.infer<typeof AgentName>;

export const RunId = UUID;

export type RunId = z.infer<typeof RunId>;

export const SessionId = UUID;

export type SessionId = z.infer<typeof SessionId>;

export const RunMode = z.enum(["sync", "async", "stream"]);

// TODO: implement is_terminal property somehow
export const RunStatus = z.enum([
  "created",
  "in-progress",
  "awaiting",
  "cancelling",
  "cancelled",
  "completed",
  "failed",
]);

export const MessageAwaitRequest = z.object({
  type: z.literal("message"),
  message: Message,
});

export const MessageAwaitResume = z.object({
  type: z.literal("message"),
  message: Message,
});

// intended to be converted to unions after more *AwaitRequest types are added
export const AwaitRequest = MessageAwaitRequest;

export type AwaitRequest = z.infer<typeof AwaitRequest>;

export const AwaitResume = MessageAwaitResume;

export type AwaitResume = z.infer<typeof AwaitResume>;

// TODO: implement raise_for_status method
export const Run = z.object({
  run_id: RunId,
  agent_name: AgentName,
  session_id: z.optional(SessionId),
  status: RunStatus.default("created"),
  await_request: AwaitRequest,
  output: z.array(Message),
  error: z.optional(ErrorModel),
  created_at: z
    .string()
    .datetime()
    .default(() => new Date().toISOString()),
  finished_at: z.string().datetime().optional(),
});

export type Run = z.infer<typeof Run>;

export const Agent = z.object({
  name: AgentName,
  description: z.string().optional(),
  metadata: Metadata.default({}),
});

export type Agent = z.infer<typeof Agent>;

export const MessageCreatedEvent = z.object({
  type: z.literal("message.created"),
  message: Message,
});

export const MessagePartEvent = z.object({
  type: z.literal("message.part"),
  part: MessagePart,
});

export const MessageCompletedEvent = z.object({
  type: z.literal("message.completed"),
  message: Message,
});

export const RunAwaitingEvent = z.object({
  type: z.literal("run.awaiting"),
  run: Run,
});

export const GenericEvent = z.object({
  type: z.literal("generic"),
  generic: AnyModel,
});

export const RunCreatedEvent = z.object({
  type: z.literal("run.created"),
  run: Run,
});

export const RunInProgressEvent = z.object({
  type: z.literal("run.in-progress"),
  run: Run,
});

export const RunFailedEvent = z.object({
  type: z.literal("run.failed"),
  run: Run,
});

export const RunCancelledEvent = z.object({
  type: z.literal("run.cancelled"),
  run: Run,
});

export const RunCompletedEvent = z.object({
  type: z.literal("run.completed"),
  run: Run,
});

export const ErrorEvent = z.object({
  type: z.literal("error"),
  error: ErrorModel,
});

export const Event = z.discriminatedUnion("type", [
  MessageCreatedEvent,
  MessagePartEvent,
  MessageCompletedEvent,
  RunAwaitingEvent,
  GenericEvent,
  RunCreatedEvent,
  RunInProgressEvent,
  RunFailedEvent,
  RunCancelledEvent,
  RunCompletedEvent,
  ErrorEvent,
]);

export type Event = z.infer<typeof Event>;
