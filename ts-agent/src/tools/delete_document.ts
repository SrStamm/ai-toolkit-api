import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { z } from "zod";

registerTool({
  name: "delete_document",
  description: "Elimina un documento con el source ingresado.",
  schema: z.object({
    source: z.string(),
  }),
  dependencies: [],
  execute: async (input, deps) => {
    const result = await httpClient.deleteDocument(input.source);
    return {
      ok: true,
      metadata: { source: result.source },
    };
  },
});
