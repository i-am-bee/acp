import { ZodType } from "zod";

export function createSchemaTypePredicate<T>(schema: ZodType<T>) {
  return (data: unknown): data is T => {
    return schema.safeParse(data).success;
  }
}
