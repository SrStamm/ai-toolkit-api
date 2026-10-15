import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { logger } from "../lib/logger";
import { z } from "zod";

const log = logger.child("tool:delete_document");

registerTool({
  name: "delete_document",
  description: "Elimina un documento con el source ingresado.",
  schema: z.object({
    source: z.string(),
  }),
  dependencies: [],
  execute: async (input, deps) => {
    log.debug("execute_start", { source: input.source });

    const startTime = Date.now();

    try {
      const result = await httpClient.deleteDocument(input.source);

      log.info("execute_completed", {
        source: result.source,
        duration_ms: Date.now() - startTime,
      });

      return {
        ok: true,
        output: `Documento ${result.source} eliminado`,
        metadata: { source: result.source },
      };
    } catch (err) {
      log.error("execute_failed", {
        source: input.source,
        duration_ms: Date.now() - startTime,
        error: err instanceof Error ? err.message : String(err),
      });
      throw err;
    }
  },
});
