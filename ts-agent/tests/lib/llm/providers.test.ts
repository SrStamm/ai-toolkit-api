import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { MistralProvider } from "../../../src/lib/llm/providers/mistral";
import { GroqProvider } from "../../../src/lib/llm/providers/groq";

describe("llm providers", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("MistralProvider", () => {
    it("prepends system prompt as first message", async () => {
      const p = new MistralProvider("https://api.mistral.ai/v1", "k", "mistral-large", 0.5);
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          model: "mistral-large",
          usage: { prompt_tokens: 1, total_tokens: 2, completion_tokens: 1 },
          choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: "hi" } }],
        }),
      });
      await p.chat([{ role: "user", content: "q" }], "sys");
      const opts = fetchMock.mock.calls[0][1] as any;
      const body = JSON.parse(opts.body);
      expect(body.messages[0]).toEqual({ role: "system", content: "sys" });
      expect(body.messages[1]).toEqual({ role: "user", content: "q" });
    });

    it("adds response_format when baseUrl contains 'mistral'", async () => {
      const p = new MistralProvider("https://api.mistral.ai/v1", "k", "m", 0.1);
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          model: "m",
          usage: { prompt_tokens: 0, total_tokens: 0, completion_tokens: 0 },
          choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: "ok" } }],
        }),
      });
      await p.chat([], "sys");
      const opts = fetchMock.mock.calls[0][1] as any;
      const body = JSON.parse(opts.body);
      expect(body.response_format).toEqual({ type: "json_object" });
    });

    it("POSTs to baseUrl/chat/completions with Bearer token", async () => {
      const p = new MistralProvider("https://api.mistral.ai/v1", "key123", "m", 0.1);
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          model: "m",
          usage: { prompt_tokens: 0, total_tokens: 0, completion_tokens: 0 },
          choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: "ok" } }],
        }),
      });
      await p.chat([], "sys");
      expect(fetchMock.mock.calls[0][0]).toBe("https://api.mistral.ai/v1/chat/completions");
      const opts = fetchMock.mock.calls[0][1] as any;
      expect(opts.method).toBe("POST");
      expect(opts.headers.Authorization).toBe("Bearer key123");
      expect(opts.headers["Content-Type"]).toBe("application/json");
    });

    it("non-ok rejects with /LLM client failed: 500/", async () => {
      const p = new MistralProvider("https://api.mistral.ai/v1", "k", "m", 0.1);
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        text: async () => "err",
      });
      await expect(p.chat([], "sys")).rejects.toThrow(/LLM client failed: 500/);
    });

    it("success maps content/usage/cost/model and provider mistral", async () => {
      const p = new MistralProvider("https://api.mistral.ai/v1", "k", "m", 0.1);
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          model: "mistral-large-latest",
          usage: { prompt_tokens: 5, total_tokens: 8, completion_tokens: 3 },
          choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: "response text" } }],
        }),
      });
      const res = await p.chat([{ role: "user", content: "q" }], "sys");
      expect(res.content).toBe("response text");
      expect(res.usage).toEqual({ prompt_tokens: 5, completion_tokens: 3, total_tokens: 8 });
      expect(res.cost).toEqual({ input_cost: 0, output_cost: 0, total_cost: 0 });
      expect(res.model).toBe("mistral-large-latest");
      expect(res.provider).toBe("mistral");
    });
  });

  describe("GroqProvider", () => {
    it("adds tools:[] and tool_choice:none and prepends system", async () => {
      const p = new GroqProvider("https://api.groq.com/openai/v1", "k", "llama", 0.2);
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          model: "llama",
          usage: { prompt_tokens: 0, total_tokens: 0, completion_tokens: 0 },
          choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: "hi" } }],
        }),
      });
      await p.chat([{ role: "user", content: "q" }], "sys");
      const opts = fetchMock.mock.calls[0][1] as any;
      const body = JSON.parse(opts.body);
      expect(body.messages[0]).toEqual({ role: "system", content: "sys" });
      expect(body.messages[1]).toEqual({ role: "user", content: "q" });
      expect(body.tools).toEqual([]);
      expect(body.tool_choice).toBe("none");
      expect(body.model).toBe("llama");
      expect(body.temperature).toBe(0.2);
    });

    it("non-ok rejects with /Groq API failed/ and includes body text", async () => {
      const p = new GroqProvider("https://api.groq.com/openai/v1", "k", "llama", 0.2);
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        text: async () => "boom",
      });
      await expect(p.chat([], "sys")).rejects.toThrow(/Groq API failed/);
    });

    it("success maps and provider is groq", async () => {
      const p = new GroqProvider("https://api.groq.com/openai/v1", "k", "llama", 0.2);
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          model: "llama-3.1",
          usage: { prompt_tokens: 2, total_tokens: 4, completion_tokens: 2 },
          choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: "groq-resp" } }],
        }),
      });
      const res = await p.chat([], "sys");
      expect(res.content).toBe("groq-resp");
      expect(res.usage).toEqual({ prompt_tokens: 2, completion_tokens: 2, total_tokens: 4 });
      expect(res.provider).toBe("groq");
      expect(res.model).toBe("llama-3.1");
    });
  });
});
