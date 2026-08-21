import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { z } from "zod";

registerTool({
  name: "get_document_metadata",
  description: "Obtiene la metadata de un documento específico.",
  schema: z.object({
    source: z.string(),
  }),
  dependencies: [],
  execute: async (input, deps) => {
    const result = await httpClient.getSourceMetadata(input.source);
    return {
      ok: true,
      output: result.output,
      metadata: result.metadata,
    };
  },
});
