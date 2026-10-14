import { vi, describe, it, expect, beforeEach } from "vitest";
import { z } from "zod";

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
});
