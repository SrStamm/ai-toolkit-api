import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { logger } from "../lib/logger";
import { z } from "zod";

const log = logger.child("tool:list_documents");

registerTool({
  name: "list_documents",
  description: "Lista los documentos disponibles en la base de conocimiento.",
  schema: z.object({
    domain: z.string().optional(),
  }),
  dependencies: [],
  execute: async (input, deps) => {
    log.debug("execute_start", { domain: input.domain });

    const startTime = Date.now();

    try {
      const result = await httpClient.listSources(input.domain);

      if (result.status === "failed") {
        log.info("execute_no_documents", {
          duration_ms: Date.now() - startTime,
        });
        return {
          ok: false,
          error: "No hay documentos en la base de conocimiento",
          retryable: false,
        };
      }

      log.info("execute_completed", {
        duration_ms: Date.now() - startTime,
        document_count: result.metadata?.count ?? 0,
      });

      return {
        ok: true,
        output: result.output,
        metadata: {
          documents: result.metadata.documents,
          count: result.metadata.count,
        },
      };
    } catch (err) {
      log.error("execute_failed", {
        duration_ms: Date.now() - startTime,
        error: err instanceof Error ? err.message : String(err),
      });
      throw err;
    }
  },
});
