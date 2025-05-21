import * as z from "zod";

export function createSchemaTypePredicate<T>(schema: z.ZodType<T>) {
  return (data: unknown): data is T => {
    return schema.safeParse(data).success;
  };
}

export const nullishObject = <T extends z.ZodRawShape>(
  schema: z.ZodObject<T>
) => {
  const nullishShape = Object.fromEntries(
    Object.entries(schema.shape).map(([key, schema]) => [key, schema.nullish()])
  ) as unknown as {
    [K in keyof T]: z.ZodNullable<z.ZodOptional<T[K]>>;
  };
  return z.object(nullishShape);
};
