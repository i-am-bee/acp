import { Message, MessagePart } from "../models/models.js";

export type Input = Message[] | Message | MessagePart[] | MessagePart | string[] | string;
