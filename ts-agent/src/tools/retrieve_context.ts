import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { logger } from "../lib/logger";
import { z } from "zod";

const log = logger.child("tool:retrieve_context");

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
    log.debug("execute_start", {
      query_preview: input.query.slice(0, 80),
      top_k: input.top_k,
      domain: input.domain,
    });

    const startTime = Date.now();

    try {
      const results = await httpClient.search(input.query, {
        topK: input.top_k,
        domain: input.domain ?? "",
        topic: input.topic,
      });

      if (!results || results.length === 0) {
        log.info("execute_no_results", {
          duration_ms: Date.now() - startTime,
        });
        return {
          ok: true,
          output:
            "No se encontró contexto relevante en la base de conocimientos para esta consulta.",
          metadata: { citations: [] },
        };
      }

      log.info("execute_completed", {
        duration_ms: Date.now() - startTime,
        context_len: results.context?.length,
        citation_count: results.citations?.length ?? 0,
      });

      return {
        ok: true,
        output: results.context,
        metadata: { citations: results.citations },
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
