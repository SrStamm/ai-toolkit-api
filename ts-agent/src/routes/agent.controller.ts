import { type Request, type Response } from "express";
import { AgentInputSchema } from "./agent.type";
import { createRuntime } from "../runtime/runtime";
import { getLlmProvider } from "../lib/llm/factory";
import { loadProvidersConfig } from "../config/loader";
import { ProviderConfigValidator } from "../config/validator";

export async function streamAgentLoop(req: Request, res: Response) {
  const parsed = AgentInputSchema.safeParse(req.body);

  if (!parsed.success) {
    res.status(400).json({
      error: "Invalid input",
      details: parsed.error.flatten().fieldErrors,
    });
    return;
  }

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
    }
  });

  try {
    const providerOverride = req.headers["x-llm-provider"] as string | undefined;
    const modelOverride = req.headers["x-llm-model"] as string | undefined;

    const llm = getLlmProvider({
      provider: providerOverride,
      model: modelOverride,
    });

    const runtime = createRuntime(llm);

    for await (const event of runtime.runStream(parsed.data)) {
      if (isAborted) break;
      res.write(event);

      if (typeof res.flush === "function") {
        res.flush();
      }
    }
  } catch (err) {
    console.error("[SLE] Error en stream:", err);
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
    const config = loadProvidersConfig();
    const validator = new ProviderConfigValidator();
    const errors = validator.validate(config);

    if (errors.length > 0) {
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

    res.json(response);
  } catch (err) {
    console.error("[providers] Error loading config:", err);
    res.status(500).json({
      error: err instanceof Error ? err.message : "Failed to load providers",
    });
  }
}
