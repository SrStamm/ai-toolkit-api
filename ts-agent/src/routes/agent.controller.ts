import { type Request, type Response } from "express";
import { AgentInputSchema } from "./agent.type";
import { createRuntime } from "../runtime/runtime";
import { getLlmProvider } from "../lib/llm/factory";

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
    const runtime = createRuntime(getLlmProvider());

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
