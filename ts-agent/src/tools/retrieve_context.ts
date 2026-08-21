import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { z } from "zod";

registerTool({
  name: "retrieve_context",
  description: "Busca contexto relevante en la base de conocimiento",
  schema: z.object({
    query: z.string(),
    opts: z.object({
      topK: z.number().optional(),
      domain: z.string(),
      topic: z.string().optional(),
    }),
  }),
  dependencies: [],
  execute: async (input, deps) => {
    const result = await httpClient.search(input.query, input.opts);
    return {
      ok: true,
      output: result.context,
      metadata: { citations: result.citations },
    };
  },
});
