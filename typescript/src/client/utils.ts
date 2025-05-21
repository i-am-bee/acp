import {
  isMessage,
  isMessagePart,
  Message,
  MessagePart,
} from "../models/models.js";
import { Input } from "./types.js";

export function inputToMessages(input: Input): Message[] {
  if (Array.isArray(input)) {
    if (!input.length) {
      return [];
    }
    if (input.every((i) => isMessage(i))) {
      return input.map(i => Message.parse(i));
    }
    if (input.every((i) => isMessagePart(i))) {
      return [Message.parse({ parts: input })];
    }
    if (input.every((i) => typeof i === "string")) {
      return [
        Message.parse({
          parts: input.map((content) => MessagePart.parse({ content })),
        }),
      ];
    }
    throw new TypeError("List with mixed types is not supported");
  } else {
    if (typeof input === "string") {
      input = MessagePart.parse({ content: input });
    }
    if (isMessagePart(input)) {
      input = Message.parse({ parts: [input] });
    }
    if (isMessage(input)) {
      input = [Message.parse(input)];
    }
    return input as Message[];
  }
}
