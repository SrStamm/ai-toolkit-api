import { describe, it, expect } from "vitest";
import { buildRoutingPrompt, buildFinalAnswerPrompt } from "../../src/router/prompts";
import type { ToolContext } from "../../src/types/agent";
import { ToolErrorCodes, type ToolError } from "../../src/types/tools";

function makeCtx(overrides: Partial<ToolContext> = {}): ToolContext {
  return {
    hasContext: false,
    toolExecutionCount: 0,
    citations: [],
    failedToolAttempts: {},
    maxToolRetries: 1,
    ...overrides,
  };
}

describe("buildRoutingPrompt", () => {
  it("includes the provided tool list text", () => {
    const prompt = buildRoutingPrompt("TOOL_LIST_SENTINEL", makeCtx());

    expect(prompt).toContain("TOOL_LIST_SENTINEL");
  });

  it("interpolates hasContext, toolExecutionCount and lastTool values", () => {
    const prompt = buildRoutingPrompt(
      "tools",
      makeCtx({ hasContext: true, toolExecutionCount: 7, lastTool: "list_documents" }),
    );

    expect(prompt).toContain("Have context: true");
    expect(prompt).toContain("Tool execution count: 7");
    expect(prompt).toContain("Last tool executed: list_documents");
  });

  it("renders None for lastTool and lastToolResult when undefined", () => {
    const prompt = buildRoutingPrompt("tools", makeCtx());

    expect(prompt).toContain("Last tool executed: None");
    expect(prompt).toContain("Last tool result: None");
  });

  it("includes lastToolResult when provided", () => {
    const prompt = buildRoutingPrompt("tools", makeCtx({ lastToolResult: "RESULT_SENTINEL" }));

    expect(prompt).toContain("Last tool result: RESULT_SENTINEL");
  });

  it("does not advertise the phantom ingest_pdf_file tool", () => {
    const prompt = buildRoutingPrompt("tools", makeCtx());

    expect(prompt).not.toContain("ingest_pdf_file");
  });

  it("does not render invalid double braces", () => {
    const prompt = buildRoutingPrompt("tools", makeCtx());

    expect(prompt).not.toContain("{{");
  });

  it("still advertises URL ingestion via ingest_document", () => {
    const prompt = buildRoutingPrompt("tools", makeCtx());

    expect(prompt).toContain("URL INGESTION FLOW");
    expect(prompt).toContain("ingest_document");
  });

  it("renders the last tool error code, retryability and message", () => {
    const lastToolError: ToolError = {
      toolName: "search",
      code: ToolErrorCodes.BAD_REQUEST,
      message: "invalid input",
      retryable: false,
      timestamp: 1700000000000,
    };
    const prompt = buildRoutingPrompt("tools", makeCtx({ lastToolError }));

    expect(prompt).toContain("Last tool error: bad_request (not retryable): invalid input");
  });
});

describe("buildFinalAnswerPrompt", () => {
  it("does not include a Context section when called without a context", () => {
    const prompt = buildFinalAnswerPrompt();

    expect(prompt).not.toContain("## Context");
  });

  it("includes the Context section and the provided context", () => {
    const prompt = buildFinalAnswerPrompt("MY_CTX");

    expect(prompt).toContain("## Context");
    expect(prompt).toContain("MY_CTX");
  });

  it("includes the Last tool failure section without a context argument", () => {
    const error: ToolError = {
      toolName: "search",
      code: ToolErrorCodes.INVALID_RESPONSE,
      message: "unexpected payload",
      retryable: false,
      timestamp: 1700000000000,
    };
    const prompt = buildFinalAnswerPrompt(undefined, error);

    expect(prompt).toContain("## Last tool failure");
    expect(prompt).toContain("INVALID_RESPONSE");
    expect(prompt).toContain("unexpected payload");
  });
});
