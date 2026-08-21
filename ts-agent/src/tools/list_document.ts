import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { z } from "zod";

registerTool({
  name: "list_documents",
  description: "Lista los documentos disponibles en la base de conocimiento.",
  schema: z.object({
    domain: z.string().optional(),
  }),
  dependencies: [],
  execute: async (input, deps) => {
    const result = await httpClient.listSources(input.domain);
    return {
      ok: true,
      output: result.output,
      metadata: {
        documents: result.metadata.documents,
        count: result.metadata.count,
      },
    };
  },
});
