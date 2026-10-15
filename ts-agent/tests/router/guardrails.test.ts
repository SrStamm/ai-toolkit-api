import { describe, it, expect } from "vitest";
import { applyGuardrails } from "../../src/router/guardrails";
import { ActionType, type Decision, type ToolContext } from "../../src/types/agent";

function makeCtx(overrides: Partial<ToolContext> = {}): ToolContext {
  return {
    hasContext: false,
    toolExecutionCount: 0,
    citations: [],
    ...overrides,
  };
}

function callTool(toolName: string): Decision {
  return { action: ActionType.CALL_TOOL, tool_name: toolName, args: {} };
}

describe("applyGuardrails", () => {
  it("blocks retrieve_context when context is already present", () => {
    const decision = callTool("retrieve_context");
    const ctx = makeCtx({ hasContext: true });

    const result = applyGuardrails(decision, ctx);

    expect(result).toEqual({ action: ActionType.FINAL_ANSWER });
  });

  it("does not block retrieve_context when there is no context", () => {
    const decision = callTool("retrieve_context");
    const ctx = makeCtx({ hasContext: false });

    const result = applyGuardrails(decision, ctx);

    expect(result).toBe(decision);
  });

  it("blocks a tool that equals ctx.lastTool", () => {
    const decision = callTool("list_documents");
    const ctx = makeCtx({ lastTool: "list_documents" });

    const result = applyGuardrails(decision, ctx);

    expect(result).toEqual({ action: ActionType.FINAL_ANSWER });
  });

  it("passes through a different tool than ctx.lastTool unchanged", () => {
    const decision = callTool("list_documents");
    const ctx = makeCtx({ lastTool: "get_document_metadata" });

    const result = applyGuardrails(decision, ctx);

    expect(result).toBe(decision);
  });

  it("passes through an ask_user decision unchanged", () => {
    const decision: Decision = { action: ActionType.ASK_USER, message: "Which domain?" };

    const result = applyGuardrails(decision, makeCtx());

    expect(result).toBe(decision);
  });

  it("passes through a final_answer decision unchanged", () => {
    const decision: Decision = { action: ActionType.FINAL_ANSWER };

    const result = applyGuardrails(decision, makeCtx());

    expect(result).toBe(decision);
  });
});
