import { type Request, type Response } from "express";
import { AgentInputSchema } from "./agent.type";
import { createRuntime } from "../runtime/runtime";
import { getLlmProvider } from "../lib/llm/factory";
import { loadProvidersConfig } from "../config/loader";
import { ProviderConfigValidator } from "../config/validator";
import { logger } from "../lib/logger";

const log = logger.child("controller");

export async function streamAgentLoop(req: Request, res: Response) {
  const parsed = AgentInputSchema.safeParse(req.body);

  if (!parsed.success) {
    log.warn("invalid_input", {
      errors: parsed.error.flatten().fieldErrors,
    });
    res.status(400).json({
      error: "Invalid input",
      details: parsed.error.flatten().fieldErrors,
    });
    return;
  }

  const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const startTime = Date.now();

  log.info("stream_request_received", {
    request_id: requestId,
    query_preview: parsed.data.query.slice(0, 100),
    session_id: parsed.data.sessionId,
    has_file: !!parsed.data.file_uuid,
    provider_header: req.headers["x-llm-provider"],
    model_header: req.headers["x-llm-model"],
  });

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();

  res.write(
    `event: state_changed\ndata: ${JSON.stringify({ type: "state_changed", state: "connecting" })}\n\n`,
  );

  let isAborted = false;

  res.on("close", () => {
    if (!res.writableEnded) {
      isAborted = true;
      log.info("stream_client_disconnected", {
        request_id: requestId,
        duration_ms: Date.now() - startTime,
      });
    }
  });

  try {
    const providerOverride = req.headers["x-llm-provider"] as string | undefined;
    const modelOverride = req.headers["x-llm-model"] as string | undefined;

    log.debug("resolving_llm_provider", {
      request_id: requestId,
      provider_override: providerOverride,
      model_override: modelOverride,
    });

    const llm = getLlmProvider({
      provider: providerOverride,
      model: modelOverride,
    });

    const runtime = createRuntime(llm);

    log.info("stream_started", { request_id: requestId });

    // Map schema fields to runtime AgentInput
    const agentInput = {
      query: parsed.data.query,
      session_id: parsed.data.sessionId,
      domain: parsed.data.domain,
      top_k: parsed.data.top_k,
      history: parsed.data.history,
      file_uuid: parsed.data.file_uuid,
      filename: parsed.data.filename,
    };

    for await (const event of runtime.runStream(agentInput)) {
      if (isAborted) break;
      res.write(event);

      if (typeof res.flush === "function") {
        res.flush();
      }
    }

    log.info("stream_finished", {
      request_id: requestId,
      duration_ms: Date.now() - startTime,
      client_aborted: isAborted,
    });
  } catch (err) {
    const durationMs = Date.now() - startTime;
    log.error("stream_error", {
      request_id: requestId,
      duration_ms: durationMs,
      error: err instanceof Error ? err.message : "Unknown error",
      stack: err instanceof Error ? err.stack : undefined,
    });
    if (!isAborted) {
      const errorEvent = `event: error\ndata: ${JSON.stringify({
        type: "error",
        error: err instanceof Error ? err.message : "Unknown error",
      })}\n\n`;
      res.write(errorEvent);
    }
  } finally {
    if (!res.writableEnded) {
      res.end();
    }
  }
}

export function listProviders(_req: Request, res: Response) {
  try {
    log.debug("list_providers_request");
    const config = loadProvidersConfig();
    const validator = new ProviderConfigValidator();
    const errors = validator.validate(config);

    if (errors.length > 0) {
      log.error("provider_config_invalid", { errors });
      res.status(500).json({
        error: "Invalid provider configuration",
        details: errors,
      });
      return;
    }

    // Map internal camelCase to frontend snake_case
    const response = {
      providers: config.providers.map((p) => ({
        name: p.name,
        default_model: p.defaultModel ?? null,
        models: p.models.map((m) => ({
          name: m.name,
          max_tokens: m.maxTokens,
          supports_tools: m.supportsTools,
        })),
      })),
    };

    log.info("list_providers_completed", {
      provider_count: config.providers.length,
    });

    res.json(response);
  } catch (err) {
    log.error("list_providers_error", {
      error: err instanceof Error ? err.message : "Failed to load providers",
    });
    res.status(500).json({
      error: err instanceof Error ? err.message : "Failed to load providers",
    });
  }
}
