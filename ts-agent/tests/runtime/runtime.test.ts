import { vi, describe, it, expect, beforeEach } from "vitest";
import { z } from "zod";
import type { Runtime } from "../../src/runtime/runtime.js";
import {
  ToolErrorCodes,
  type Tool,
  type ToolError,
  type ToolResult,
} from "../../src/types/tools";

vi.mock("ioredis", () => ({
  Redis: class {
    on() {}
  },
}));

describe("runtime", () => {
  let fakeLlm: any;
  let fakeMemory: any;

  const llmReply = (content: string) => ({
    content,
    usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
    cost: { input_cost: 0, output_cost: 0, total_cost: 0 },
    model: "m",
    provider: "p",
  });

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    fakeLlm = {
      chat: vi.fn(),
    };
    fakeMemory = {
      add: vi.fn().mockResolvedValue(undefined),
      getHistory: vi.fn().mockResolvedValue([]),
    };
  });

  describe("extractAnswer", () => {
    it("handles empty and trim", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory);
      expect(rt.extractAnswer("")).toBe("");
      expect(rt.extractAnswer("  hello  ")).toBe("hello");
    });

    it("strips code fences and extracts common fields", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory);
      expect(rt.extractAnswer("```json\n{\"answer\":\"hi\"}\n```")).toBe("{\"answer\":\"hi\"}");
      expect(rt.extractAnswer("{\"response\":\"hi\"}")).toBe("hi");
      expect(rt.extractAnswer("{\"content\":\"hi\"}")).toBe("hi");
      expect(rt.extractAnswer("{\"message\":\"hi\"}")).toBe("hi");
    });

    it("handles single-key and non-JSON", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory);
      expect(rt.extractAnswer("{\"foo\":\"bar\"}")).toBe("bar");
      expect(rt.extractAnswer("{\"answer\":\"a\",\"other\":\"b\"}")).toBe("a");
      expect(rt.extractAnswer("{ not json }")).toBe("{ not json }");
    });
  });

  describe("runStream", () => {
    it("ASK_USER produces expected events and stops", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 4, retryBackoffMs: 1 });
      fakeLlm.chat.mockResolvedValueOnce(llmReply(JSON.stringify({ action: "ask_user", message: "dame dominio" })));
      const events: Array<{ event: string; data: any }> = [];
      for await (const c of rt.runStream({ query: "hi" })) {
        const lines = c.split("\n");
        let ev = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          if (line.startsWith("data:")) dataStr = line.slice(5).trim();
        }
        if (ev && dataStr) events.push({ event: ev, data: JSON.parse(dataStr) });
      }
      expect(events.map((e) => e.event)).toEqual([
        "state_changed",
        "agent_decision",
        "state_changed",
        "llm_token",
        "done",
      ]);
      expect(events[1].data.decision.action).toBe("ask_user");
      expect(events[3].data.token).toBe("dame dominio");
      expect(fakeLlm.chat).toHaveBeenCalledTimes(1);
    });

    it("FINAL_ANSWER streams answer and saves memory", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 4, retryBackoffMs: 1 });
      fakeLlm.chat
        .mockResolvedValueOnce(llmReply(JSON.stringify({ action: "final_answer" })))
        .mockResolvedValueOnce(llmReply("LA RESPUESTA"));
      const events: Array<{ event: string; data: any }> = [];
      for await (const c of rt.runStream({ query: "hi" })) {
        const lines = c.split("\n");
        let ev = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          if (line.startsWith("data:")) dataStr = line.slice(5).trim();
        }
        if (ev && dataStr) events.push({ event: ev, data: JSON.parse(dataStr) });
      }
      const eventNames = events.map((e) => e.event);
      expect(eventNames).toContain("state_changed");
      expect(eventNames).toContain("llm_token");
      expect(eventNames).toContain("done");
      expect(events.some((e) => e.event === "llm_token" && e.data.token === "LA RESPUESTA")).toBe(true);
      expect(fakeMemory.add).toHaveBeenCalled();
      const lastCall = fakeMemory.add.mock.calls[fakeMemory.add.mock.calls.length - 1];
      expect(lastCall[1]).toMatchObject({ role: "assistant" });
    });

    it("Unknown tool results in tool_done error", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 4, retryBackoffMs: 1 });
      fakeLlm.chat
        .mockResolvedValueOnce(llmReply(JSON.stringify({ action: "call_tool", tool_name: "nope", args: {} })))
        .mockResolvedValueOnce(llmReply(JSON.stringify({ action: "final_answer" })))
        .mockResolvedValueOnce(llmReply("done"));
      const events: Array<{ event: string; data: any }> = [];
      for await (const c of rt.runStream({ query: "hi" })) {
        const lines = c.split("\n");
        let ev = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          if (line.startsWith("data:")) dataStr = line.slice(5).trim();
        }
        if (ev && dataStr) events.push({ event: ev, data: JSON.parse(dataStr) });
      }
      const toolDone = events.find((e) => e.event === "tool_done");
      expect(toolDone).toBeDefined();
      expect(toolDone?.data.status).toBe("error");
    });

    it("Tool complete early-return emits tool_done success and llm_token with output", async () => {
      const { registerTool } = await import("../../src/tools/registry.js");
      registerTool({
        name: "__t_complete",
        description: "",
        schema: z.object({}),
        dependencies: [],
        execute: async () => ({ ok: true, complete: true, output: "DONE", metadata: {} as any }),
      });
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 4, retryBackoffMs: 1 });
      fakeLlm.chat.mockResolvedValueOnce(
        llmReply(JSON.stringify({ action: "call_tool", tool_name: "__t_complete", args: {} })),
      );
      const events: Array<{ event: string; data: any }> = [];
      for await (const c of rt.runStream({ query: "hi" })) {
        const lines = c.split("\n");
        let ev = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          if (line.startsWith("data:")) dataStr = line.slice(5).trim();
        }
        if (ev && dataStr) events.push({ event: ev, data: JSON.parse(dataStr) });
      }
      const toolDone = events.find((e) => e.event === "tool_done");
      expect(toolDone?.data.status).toBe("success");
      expect(events.some((e) => e.event === "llm_token" && e.data.token === "DONE")).toBe(true);
      expect(events.some((e) => e.event === "done")).toBe(true);
      expect(events.some((e) => e.event === "state_changed" && e.data.state === "completed")).toBe(true);
      expect(fakeLlm.chat).toHaveBeenCalledTimes(1);
    });
  });

  describe("runStream failure handling", () => {
    type StreamEventPayload = {
      event: string;
      data: { type: string; state?: string; error?: string };
    };

    const collectEvents = async (
      rt: Runtime,
      query: string,
    ): Promise<StreamEventPayload[]> => {
      const events: StreamEventPayload[] = [];
      for await (const chunk of rt.runStream({ query })) {
        const lines = chunk.split("\n");
        let ev = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          if (line.startsWith("data:")) dataStr = line.slice(5).trim();
        }
        if (ev && dataStr) events.push({ event: ev, data: JSON.parse(dataStr) });
      }
      return events;
    };

    it("emits a failed state and an error event when maxSteps is exhausted", async () => {
      const { registerTool } = await import("../../src/tools/registry.js");
      const incompleteTool = {
        description: "",
        schema: z.object({}),
        dependencies: [],
        execute: async () => ({
          ok: true as const,
          complete: false,
          output: "partial",
          metadata: {},
        }),
      };
      registerTool({ name: "__t_loop_a", ...incompleteTool });
      registerTool({ name: "__t_loop_b", ...incompleteTool });

      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 3, retryBackoffMs: 1 });
      // Alternate tools so the repeat-tool guardrail never short-circuits the loop
      fakeLlm.chat
        .mockResolvedValueOnce(
          llmReply(JSON.stringify({ action: "call_tool", tool_name: "__t_loop_a", args: {} })),
        )
        .mockResolvedValueOnce(
          llmReply(JSON.stringify({ action: "call_tool", tool_name: "__t_loop_b", args: {} })),
        )
        .mockResolvedValueOnce(
          llmReply(JSON.stringify({ action: "call_tool", tool_name: "__t_loop_a", args: {} })),
        )
        .mockResolvedValue(
          llmReply(JSON.stringify({ action: "call_tool", tool_name: "__t_loop_a", args: {} })),
        );

      const events = await collectEvents(rt, "hi");

      expect(events.some((e) => e.event === "done")).toBe(false);

      const failedIdx = events.findIndex(
        (e) => e.event === "state_changed" && e.data.state === "failed",
      );
      const errorIdx = events.findIndex((e) => e.event === "error");

      expect(failedIdx).toBeGreaterThanOrEqual(0);
      expect(errorIdx).toBeGreaterThan(failedIdx);

      const errorEvent = events[errorIdx];
      expect(typeof errorEvent.data.error).toBe("string");
      expect(errorEvent.data.error).toContain("maximum number of steps");
      expect(errorEvent.data.error).not.toContain("\n");
    });

    it("turns an unexpected runtime error into a failed state and an error event", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 2, retryBackoffMs: 1 });
      fakeLlm.chat.mockRejectedValue(new Error("provider exploded"));

      // The generator must not throw: the failure is reported as events
      const events = await collectEvents(rt, "hi");

      expect(events.some((e) => e.event === "done")).toBe(false);
      expect(
        events.some((e) => e.event === "state_changed" && e.data.state === "failed"),
      ).toBe(true);

      const errorEvent = events.find((e) => e.event === "error");
      expect(errorEvent?.data.error).toBe("provider exploded");
      expect(errorEvent?.data.error).not.toContain("\n");
      expect(errorEvent?.data.error).not.toContain("runtime.ts");
    });

    it("handles non Error rejections without leaking a stack trace", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 2, retryBackoffMs: 1 });
      fakeLlm.chat.mockRejectedValue("boom");

      const events = await collectEvents(rt, "hi");

      const errorEvent = events.find((e) => e.event === "error");
      expect(errorEvent?.data.error).toBe("boom");
      expect(errorEvent?.data.error).not.toContain("at ");
    });

    it("keeps the success path unchanged: done + completed and no error event", async () => {
      const { Runtime } = await import("../../src/runtime/runtime.js");
      const rt = new Runtime(fakeLlm, fakeMemory, { maxSteps: 4, retryBackoffMs: 1 });
      fakeLlm.chat
        .mockResolvedValueOnce(llmReply(JSON.stringify({ action: "final_answer" })))
        .mockResolvedValueOnce(llmReply("LA RESPUESTA"));

      const events = await collectEvents(rt, "hi");

      expect(events.some((e) => e.event === "error")).toBe(false);
      expect(events.some((e) => e.event === "done")).toBe(true);
      expect(
        events.some((e) => e.event === "state_changed" && e.data.state === "completed"),
      ).toBe(true);
    });
  });

  describe("runStream tool error handling", () => {
    type CapturedEvent = {
      event: string;
      data: {
        type: string;
        state?: string;
        tool?: string;
        status?: string;
        step?: number;
        token?: string;
        content?: string;
        error?: ToolError | string;
        decision?: { action: string; tool_name?: string };
      };
    };

    const collectToolEvents = async (
      rt: Runtime,
      query = "hi",
    ): Promise<CapturedEvent[]> => {
      const events: CapturedEvent[] = [];
      for await (const chunk of rt.runStream({ query })) {
        const lines = chunk.split("\n");
        let ev = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          if (line.startsWith("data:")) dataStr = line.slice(5).trim();
        }
        if (ev && dataStr) events.push({ event: ev, data: JSON.parse(dataStr) });
      }
      return events;
    };

    const registerTestTool = async (
      name: string,
      execute: Tool["execute"],
    ): Promise<void> => {
      const { registerTool } = await import("../../src/tools/registry.js");
      registerTool({
        name,
        description: "",
        schema: z.object({}),
        dependencies: [],
        execute,
      });
    };

    const loadRuntime = async () => {
      const { Runtime: RuntimeClass } = await import("../../src/runtime/runtime.js");
      return RuntimeClass;
    };

    const callToolReply = (name: string) =>
      llmReply(
        JSON.stringify({ action: "call_tool", tool_name: name, args: {} }),
      );

    const finalAnswerReply = () =>
      llmReply(JSON.stringify({ action: "final_answer" }));

    const toolErrorFrom = (events: CapturedEvent[]): ToolError => {
      const event = events.find((e) => e.event === "tool_error");
      expect(event).toBeDefined();
      return event?.data.error as ToolError;
    };

    const toolDoneEvents = (events: CapturedEvent[]) =>
      events.filter((e) => e.event === "tool_done");

    const baseConfig = {
      maxSteps: 3,
      stepTimeoutMs: 1_000,
      totalTimeoutMs: 5_000,
      retryBackoffMs: 1,
    };

    it("emits tool_done success and no tool_error when a non-complete tool succeeds", async () => {
      await registerTestTool("__te_success", async () => ({
        ok: true,
        complete: false,
        output: "partial",
        metadata: {},
      }));
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 0,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_success"))
        .mockResolvedValueOnce(finalAnswerReply())
        .mockResolvedValueOnce(llmReply("final text"));

      const events = await collectToolEvents(rt);

      expect(toolDoneEvents(events)).toHaveLength(1);
      expect(toolDoneEvents(events)[0].data.status).toBe("success");
      expect(events.some((e) => e.event === "tool_error")).toBe(false);
      expect(events.some((e) => e.event === "error")).toBe(false);
      expect(events.some((e) => e.event === "llm_token" && e.data.token === "final text")).toBe(true);
    });

    it("retries a retryable tool failure and reports the eventual success", async () => {
      const execute = vi
        .fn()
        .mockResolvedValueOnce({ ok: false, error: "temporary", retryable: true })
        .mockResolvedValueOnce({
          ok: true,
          complete: true,
          output: "OK",
          metadata: {},
        });
      await registerTestTool("__te_retry", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 1,
      });
      fakeLlm.chat.mockResolvedValueOnce(callToolReply("__te_retry"));

      const events = await collectToolEvents(rt);

      expect(execute).toHaveBeenCalledTimes(2);
      expect(toolDoneEvents(events)).toHaveLength(1);
      expect(toolDoneEvents(events)[0].data.status).toBe("success");
      expect(events.some((e) => e.event === "tool_error")).toBe(false);
      expect(events.some((e) => e.event === "llm_token" && e.data.token === "OK")).toBe(true);
    });

    it("reports a NETWORK_ERROR after exhausting retries on a TypeError", async () => {
      const execute = vi.fn().mockRejectedValue(new TypeError("fetch failed"));
      await registerTestTool("__te_network", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 1,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_network"))
        .mockResolvedValueOnce(finalAnswerReply())
        .mockResolvedValueOnce(llmReply("unavailable"));

      const events = await collectToolEvents(rt);
      const error = toolErrorFrom(events);

      expect(execute).toHaveBeenCalledTimes(2);
      expect(error.code).toBe("NETWORK_ERROR");
      expect(error.retryable).toBe(true);
      expect(toolDoneEvents(events)[0].data.status).toBe("error");
    });

    it("classifies an aborted tool execution as TIMEOUT", async () => {
      const execute = vi.fn(
        (_input: unknown, _deps: unknown, signal?: AbortSignal) =>
          new Promise<ToolResult>((_resolve, reject) => {
            signal?.addEventListener("abort", () =>
              reject(new Error("tool aborted")),
            );
          }),
      );
      await registerTestTool("__te_timeout", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        stepTimeoutMs: 5,
        maxRetries: 0,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_timeout"))
        .mockResolvedValueOnce(finalAnswerReply())
        .mockResolvedValueOnce(llmReply("unavailable"));

      const events = await collectToolEvents(rt);

      expect(toolErrorFrom(events).code).toBe("TIMEOUT");
      expect(toolDoneEvents(events)[0].data.status).toBe("error");
    });

    it("does not retry a non-retryable HTTP error", async () => {
      const { HttpToolError } = await import("../../src/types/tool-error.js");
      const execute = vi
        .fn()
        .mockRejectedValue(
          new HttpToolError(400, ToolErrorCodes.BAD_REQUEST, "bad request"),
        );
      await registerTestTool("__te_http400", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 1,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_http400"))
        .mockResolvedValueOnce(finalAnswerReply())
        .mockResolvedValueOnce(llmReply("unavailable"));

      const events = await collectToolEvents(rt);
      const error = toolErrorFrom(events);

      expect(execute).toHaveBeenCalledTimes(1);
      expect(error.code).toBe("bad_request");
      expect(error.retryable).toBe(false);
      expect(error.message).toBe("bad request");
      expect(toolDoneEvents(events)[0].data.status).toBe("error");
    });

    it("retries a retryable HTTP error once and keeps the http_error code", async () => {
      const { HttpToolError } = await import("../../src/types/tool-error.js");
      const execute = vi
        .fn()
        .mockRejectedValue(
          new HttpToolError(500, ToolErrorCodes.HTTP_5XX, "server error"),
        );
      await registerTestTool("__te_http500", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 1,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_http500"))
        .mockResolvedValueOnce(finalAnswerReply())
        .mockResolvedValueOnce(llmReply("unavailable"));

      const events = await collectToolEvents(rt);
      const error = toolErrorFrom(events);

      expect(execute).toHaveBeenCalledTimes(2);
      expect(error.code).toBe("http_error");
      expect(error.retryable).toBe(true);
      expect(toolDoneEvents(events)[0].data.status).toBe("error");
    });

    it("reports INVALID_RESPONSE without retrying a malformed tool result", async () => {
      const execute = vi
        .fn()
        .mockResolvedValue("not a tool result" as unknown as ToolResult);
      await registerTestTool("__te_invalid", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 1,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_invalid"))
        .mockResolvedValueOnce(finalAnswerReply())
        .mockResolvedValueOnce(llmReply("unavailable"));

      const events = await collectToolEvents(rt);
      const error = toolErrorFrom(events);

      expect(execute).toHaveBeenCalledTimes(1);
      expect(error.code).toBe("INVALID_RESPONSE");
      expect(error.retryable).toBe(false);
      expect(toolDoneEvents(events)[0].data.status).toBe("error");
    });

    it("adds the structured error to the next routing prompt and guardrails a same-tool retry", async () => {
      const { HttpToolError } = await import("../../src/types/tool-error.js");
      const execute = vi
        .fn()
        .mockRejectedValue(
          new HttpToolError(400, ToolErrorCodes.BAD_REQUEST, "invalid input"),
        );
      await registerTestTool("__te_decision", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 0,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_decision"))
        .mockResolvedValueOnce(callToolReply("__te_decision"))
        .mockResolvedValueOnce(llmReply("The information is unavailable."));

      const events = await collectToolEvents(rt);
      const decisionCalls = JSON.stringify(fakeLlm.chat.mock.calls[1]);

      expect(decisionCalls).toContain("Last tool error:");
      expect(decisionCalls).toContain("bad_request");
      expect(decisionCalls).toContain("not retryable");
      expect(decisionCalls).toContain("invalid input");
      const decisions = events.filter((e) => e.event === "agent_decision");
      expect(decisions[1].data.decision?.action).toBe("final_answer");
      expect(toolDoneEvents(events)).toHaveLength(1);
      expect(execute).toHaveBeenCalledTimes(1);
    });

    it("communicates a definitive failure without leaking the raw error details", async () => {
      const { HttpToolError } = await import("../../src/types/tool-error.js");
      const execute = vi.fn().mockRejectedValue(
        new HttpToolError(
          400,
          ToolErrorCodes.BAD_REQUEST,
          "bad request  https://secret.example/?token=TOPSECRET123\n at handler",
        ),
      );
      await registerTestTool("__te_final", execute as Tool["execute"]);
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 0,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_final"))
        .mockResolvedValueOnce(finalAnswerReply());

      const events = await collectToolEvents(rt);
      const error = toolErrorFrom(events);
      const doneEvent = events.find((e) => e.event === "done");
      const content = String(doneEvent?.data.content);

      expect(error.message).toBe("bad request [url]");
      expect(error.message).not.toContain("\n");
      expect(error.message).not.toContain("https://");
      expect(error.message).not.toContain("TOPSECRET123");
      expect(error.message).not.toContain("at ");
      expect(fakeLlm.chat).toHaveBeenCalledTimes(2);
      expect(content).toBe(
        "No pude obtener la información solicitada: la consulta falló y no hay datos disponibles. Intentá de nuevo o reformulá la pregunta.",
      );
      expect(content).not.toContain("https://");
      expect(content).not.toContain("TOPSECRET123");
      expect(content).not.toContain("secret.example");
      expect(content).not.toContain("bad request");
      expect(content).not.toContain("handler");
      expect(content).not.toContain("\n");
    });

    it("generates the fixed no-data answer without a third LLM call", async () => {
      await registerTestTool("__te_no_data_deterministic", async () => {
        throw new Error("boom");
      });
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 0,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_no_data_deterministic"))
        .mockResolvedValueOnce(finalAnswerReply());

      const events = await collectToolEvents(rt);
      const expectedAnswer =
        "No pude obtener la información solicitada: la consulta falló y no hay datos disponibles. Intentá de nuevo o reformulá la pregunta.";

      expect(events.some((e) => e.event === "llm_token" && e.data.token === expectedAnswer)).toBe(true);
      expect(events.some((e) => e.event === "done" && e.data.content === expectedAnswer)).toBe(true);
      expect(events.some((e) => e.event === "error")).toBe(false);
      expect(fakeLlm.chat).toHaveBeenCalledTimes(2);
    });

    it("orders tool_error as a non-terminal event between executing_tool and tool_done", async () => {
      await registerTestTool("__te_order", async () => {
        throw new Error("boom");
      });
      const RuntimeClass = await loadRuntime();
      const rt = new RuntimeClass(fakeLlm, fakeMemory, {
        ...baseConfig,
        maxRetries: 0,
      });
      fakeLlm.chat
        .mockResolvedValueOnce(callToolReply("__te_order"))
        .mockResolvedValueOnce(finalAnswerReply())
        .mockResolvedValueOnce(llmReply("unavailable"));

      const events = await collectToolEvents(rt);
      const executingIdx = events.findIndex(
        (e) => e.event === "state_changed" && e.data.state === "executing_tool",
      );
      const errorIdx = events.findIndex((e) => e.event === "tool_error");
      const doneIdx = events.findIndex((e) => e.event === "tool_done");
      const error = toolErrorFrom(events);

      expect(executingIdx).toBeGreaterThanOrEqual(0);
      expect(errorIdx).toBeGreaterThan(executingIdx);
      expect(doneIdx).toBeGreaterThan(errorIdx);
      expect(events[doneIdx].data.status).toBe("error");
      expect(events.some((e) => e.event === "error")).toBe(false);
      expect(
        events.some((e) => e.event === "state_changed" && e.data.state === "failed"),
      ).toBe(false);
      expect(error.toolName).toBe("__te_order");
      expect(typeof error.code).toBe("string");
      expect(typeof error.message).toBe("string");
      expect(typeof error.retryable).toBe("boolean");
      expect(typeof error.timestamp).toBe("number");
      expect(error.message.length).toBeLessThanOrEqual(503);
    });
  });
});
