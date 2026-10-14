import { describe, it, expect, vi } from "vitest";
import { Router } from "../../src/router/router";
import type { LLMInterface } from "../../src/lib/llm/client";
import type { LLMResponse } from "../../src/types/llm";
import { ActionType, type ToolContext } from "../../src/types/agent";

function makeResponse(content: string): LLMResponse {
  return {
    content,
    usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
    cost: { input_cost: 0, output_cost: 0, total_cost: 0 },
    model: "test",
    provider: "test",
  };
}

function makeCtx(overrides: Partial<ToolContext> = {}): ToolContext {
  return {
    hasContext: false,
    toolExecutionCount: 0,
    citations: [],
    ...overrides,
  };
}

function createRouter(content: string): { router: Router; chat: ReturnType<typeof vi.fn> } {
  const chat = vi.fn().mockResolvedValue(makeResponse(content));
  const llm = { chat } as unknown as LLMInterface;
  return { router: new Router(llm), chat };
}

describe("Router.getDecision", () => {
  it("returns a call_tool decision with its args", async () => {
    const { router } = createRouter(
      '{"action":"call_tool","tool_name":"list_documents","args":{"domain":"fastapi"}}',
    );

    const decision = await router.getDecision("list docs", makeCtx());

    expect(decision).toEqual({
      action: ActionType.CALL_TOOL,
      tool_name: "list_documents",
      args: { domain: "fastapi" },
    });
  });

  it("defaults args to an empty object when call_tool has no args", async () => {
    const { router } = createRouter('{"action":"call_tool","tool_name":"list_documents"}');

    const decision = await router.getDecision("list docs", makeCtx());

    expect(decision).toEqual({
      action: ActionType.CALL_TOOL,
      tool_name: "list_documents",
      args: {},
    });
  });

  it("returns a final_answer decision", async () => {
    const { router } = createRouter('{"action":"final_answer"}');

    const decision = await router.getDecision("hola", makeCtx());

    expect(decision).toEqual({ action: ActionType.FINAL_ANSWER });
  });

  it("returns an ask_user decision with a top-level message", async () => {
    const { router } = createRouter('{"action":"ask_user","message":"top-level msg"}');

    const decision = await router.getDecision("ingest this", makeCtx());

    expect(decision).toEqual({ action: ActionType.ASK_USER, message: "top-level msg" });
  });

  it("returns an ask_user decision with a nested args.message", async () => {
    const { router } = createRouter('{"action":"ask_user","args":{"message":"nested msg"}}');

    const decision = await router.getDecision("ingest this", makeCtx());

    expect(decision).toEqual({ action: ActionType.ASK_USER, message: "nested msg" });
  });

  it("falls back to final_answer on invalid JSON content", async () => {
    const { router } = createRouter("not json");

    const decision = await router.getDecision("hola", makeCtx());

    expect(decision).toEqual({ action: ActionType.FINAL_ANSWER });
  });

  it("falls back to final_answer on valid JSON with an unknown shape", async () => {
    const { router } = createRouter('{"foo":1}');

    const decision = await router.getDecision("hola", makeCtx());

    expect(decision).toEqual({ action: ActionType.FINAL_ANSWER });
  });

  it("applies the retrieve_context guardrail when context already exists", async () => {
    const { router } = createRouter(
      '{"action":"call_tool","tool_name":"retrieve_context","args":{}}',
    );

    const decision = await router.getDecision("more context", makeCtx({ hasContext: true }));

    expect(decision).toEqual({ action: ActionType.FINAL_ANSWER });
  });

  it("applies the repeated-tool guardrail when the tool equals ctx.lastTool", async () => {
    const { router } = createRouter('{"action":"call_tool","tool_name":"list_documents"}');

    const decision = await router.getDecision(
      "list docs again",
      makeCtx({ lastTool: "list_documents" }),
    );

    expect(decision).toEqual({ action: ActionType.FINAL_ANSWER });
  });

  it("passes through an unknown tool name without validating its existence", async () => {
    const { router } = createRouter('{"action":"call_tool","tool_name":"nope"}');

    const decision = await router.getDecision("do the unknown thing", makeCtx());

    expect(decision).toEqual({
      action: ActionType.CALL_TOOL,
      tool_name: "nope",
      args: {},
    });
  });
});
