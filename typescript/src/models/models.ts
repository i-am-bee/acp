import * as z from "zod";
import { Simplify } from "type-fest";
import { ErrorModel } from "./errors.js";
import { createSchemaTypePredicate, nullishObject } from "./utils.js";
import { ACPError } from "../client/errors.js";

export const AnyModel = z.record(z.any());

export const Author = z.object({
  name: z.string(),
  email: z.string().nullish(),
  url: z.string().url().nullish(),
});

export const Contributor = z.object({
  name: z.string(),
  email: z.string().nullish(),
  url: z.string().url().nullish(),
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

export const Metadata = nullishObject(
  z.object({
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
).passthrough();

const BaseMessagePart = z
  .object({
    name: z.string().nullish(),
    content_type: z.string().nullish().default("text/plain"),
    content: z.string().nullish(),
    content_encoding: z.enum(["plain", "base64"]).nullish().default("plain"),
    content_url: z.string().url().nullish(),
  })
  .passthrough();

const refineMessagePart = (
  val: z.infer<typeof BaseMessagePart>,
  ctx: z.RefinementCtx
): never => {
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

export const Message = z.object({
  role: z
    .string()
    .regex(/^(user|agent(\/[a-zA-Z0-9_\-]+)?)$/)
    .default("user"),
  parts: z.array(MessagePart),
  created_at: z
    .string()
    .datetime()
    .nullable()
    .default(() => new Date().toISOString()),
  completed_at: z
    .string()
    .datetime()
    .nullable()
    .default(() => new Date().toISOString()),
});

export type Message = z.infer<typeof Message>;

export const isMessage = createSchemaTypePredicate(Message);

export function concatMessages(lhs: Message, rhs: Message): Message {
  if (lhs.role != rhs.role) {
    throw new Error("Message roles must match for concatenation");
  }

  return {
    role: lhs.role,
    parts: [...lhs.parts, ...rhs.parts],
    created_at:
      lhs.created_at != null && rhs.created_at != null
        ? lhs.created_at < rhs.created_at
          ? lhs.created_at
          : rhs.created_at
        : null,
    completed_at:
      lhs.completed_at != null && rhs.completed_at != null
        ? lhs.completed_at > rhs.completed_at
          ? lhs.completed_at
          : rhs.completed_at
        : null,
  };
}

export function compressMessage(message: Message): Message {
  const canBeJoined = (a: MessagePart, b: MessagePart) => {
    return (
      a.name == null &&
      b.name == null &&
      a.content_type === "text/plain" &&
      b.content_type === "text/plain" &&
      a.content_encoding === "plain" &&
      b.content_encoding === "plain" &&
      a.content_url == null &&
      b.content_url == null
    );
  };

  const join = (a: MessagePart, b: MessagePart): MessagePart => ({
    name: null,
    content_type: "text/plain",
    content: (a.content ?? "") + (b.content ?? ""),
    content_encoding: "plain",
    content_url: null,
  });

  const compressedParts: MessagePart[] = [];

  for (const part of message.parts) {
    if (
      compressedParts.length > 0 &&
      canBeJoined(compressedParts[compressedParts.length - 1], part)
    ) {
      const last = compressedParts.pop()!;
      compressedParts.push(join(last, part));
    } else {
      compressedParts.push(part);
    }
  }

  return { ...message, parts: compressedParts };
}

const UUID = z.string().uuid();

export const AgentName = z.string();

export type AgentName = z.infer<typeof AgentName>;

export const RunId = UUID;

export type RunId = z.infer<typeof RunId>;

export const SessionId = UUID;

export type SessionId = z.infer<typeof SessionId>;

export const RunMode = z.enum(["sync", "async", "stream"]);

export type RunMode = z.infer<typeof RunMode>;

export const RunStatus = z.enum([
  "created",
  "in-progress",
  "awaiting",
  "cancelling",
  "cancelled",
  "completed",
  "failed",
]);

export type RunStatus = z.infer<typeof RunStatus>;

export function isTerminalRunStatus(status: RunStatus) {
  return (
    status === "completed" || status === "cancelled" || status === "failed"
  );
}

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

export const Run = z.object({
  run_id: RunId,
  agent_name: AgentName,
  session_id: SessionId.nullish(),
  status: RunStatus.default("created"),
  await_request: AwaitRequest.nullish(),
  output: z.array(Message).default([]),
  error: ErrorModel.nullish(),
  created_at: z
    .string()
    .datetime()
    .default(() => new Date().toISOString()),
  finished_at: z.string().datetime().nullish(),
});

export type Run = z.infer<typeof Run>;

export function throwForRunStatus(run: Run) {
  if (run.status === "cancelled") {
    // throw DOMException with AbortError name like AbortController does
    throw new DOMException("Run has been cancelled", "AbortError");
  }
  if (run.status === "failed") {
    throw new ACPError(run.error!);
  }
  return run;
}

export const AgentManifest = z.object({
  name: AgentName,
  description: z.string().nullish(),
  metadata: Metadata.default({}),
});

export type AgentManifest = z.infer<typeof AgentManifest>;

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
