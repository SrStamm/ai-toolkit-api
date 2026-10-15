import { registerTool } from "./registry";
import { httpClient } from "../lib/rag-client";
import { logger } from "../lib/logger";
import { z } from "zod";

const log = logger.child("tool:ingest_document");

registerTool({
  name: "ingest_document",
  description:
    "Ingest a document from a URL into the knowledge base. " +
    "Dispatches an async job and returns a job_id the frontend can poll for progress.",
  schema: z.object({
    url: z.string().url(),
    domain: z.string(),
    topic: z.string(),
  }),
  dependencies: [],
  execute: async (input) => {
    log.debug("execute_start", { url: input.url, domain: input.domain });

    const startTime = Date.now();

    try {
      const result = await httpClient.ingest({
        url: input.url,
        source: input.url,
        domain: input.domain,
        topic: input.topic,
      });

      log.info("execute_completed", {
        job_id: result.job_id,
        duration_ms: Date.now() - startTime,
      });

      return {
        ok: true,
        complete: true,
        output: `Ingestion job queued. Job ID: ${result.job_id}`,
        metadata: { job_id: result.job_id, status: result.status },
      };
    } catch (err) {
      log.error("execute_failed", {
        url: input.url,
        duration_ms: Date.now() - startTime,
        error: err instanceof Error ? err.message : String(err),
      });
      throw err;
    }
  },
});
