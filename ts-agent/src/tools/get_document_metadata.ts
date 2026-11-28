import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { logger } from "../lib/logger";
import { z } from "zod";

const log = logger.child("tool:get_document_metadata");

registerTool({
  name: "get_document_metadata",
  description: "Obtiene la metadata de un documento específico.",
  schema: z.object({
    source: z.string(),
  }),
  dependencies: [],
  execute: async (input, deps, signal) => {
    log.debug("execute_start", { source: input.source });

    const startTime = Date.now();

    try {
      const result = await httpClient.getSourceMetadata(input.source, signal);

      log.info("execute_completed", {
        source: input.source,
        duration_ms: Date.now() - startTime,
      });

      return {
        ok: true,
        output: result.output,
        metadata: result.metadata,
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
