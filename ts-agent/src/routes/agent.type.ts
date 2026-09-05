import { z } from "zod";

export const AgentInputSchema = z.object({
  query: z.string().min(1, "Query is required"),
  sessionId: z.string().min(1, "Session ID is required"),
  domain: z.string().optional(),
  top_k: z.number().int().positive().optional(),
  history: z
    .array(
      z.object({
        role: z.enum(["user", "assistant", "system"]),
        content: z.string(),
      }),
    )
    .optional(),
  file_uuid: z.string().optional(),
  filename: z.string().optional(),
});

export type AgentInput = z.infer<typeof AgentInputSchema>;
