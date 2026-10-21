import { vi, describe, it, expect, beforeEach } from "vitest";
import { z } from "zod";
import type { Runtime } from "../../src/runtime/runtime.js";

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
});
