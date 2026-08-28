import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { z } from "zod";

registerTool({
  name: "retrieve_context",
  description: "Busca contexto relevante en la base de conocimiento",
  schema: z.object({
    query: z.string(),
    top_k: z.number().optional(),
    domain: z.string().optional(),
    topic: z.string().optional(),
  }),
  dependencies: [],
  execute: async (input, deps) => {
    const result = await httpClient.search(input.query, {
      topK: input.top_k,
      domain: input.domain ?? "",
      topic: input.topic,
    });
    return {
      ok: true,
      complete: true,
      output: result.context,
      metadata: { citations: result.citations },
    };
  },
});
