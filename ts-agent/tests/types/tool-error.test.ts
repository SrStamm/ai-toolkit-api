import { describe, it, expect } from "vitest";
import {
  HttpToolError,
  isToolResult,
  MAX_ERROR_MESSAGE_LENGTH,
  sanitizeMessage,
  toToolError,
} from "../../src/types/tool-error";
import { ToolErrorCodes } from "../../src/types/tools";

describe("sanitizeMessage", () => {
  it("keeps only the first line of an error message", () => {
    expect(sanitizeMessage(new Error("first line\nsecond line"))).toBe(
      "first line",
    );
  });

  it("replaces URLs with [url]", () => {
    expect(sanitizeMessage("see https://example.com/a?b=1 now")).toBe(
      "see [url] now",
    );
  });

  it("collapses whitespace", () => {
    expect(sanitizeMessage("a   b\t c")).toBe("a b c");
  });

  it("caps long messages at 500 characters plus an ellipsis", () => {
    const sanitized = sanitizeMessage("x".repeat(600));

    expect(sanitized).toHaveLength(MAX_ERROR_MESSAGE_LENGTH + 3);
    expect(sanitized.endsWith("...")).toBe(true);
  });
});

describe("toToolError", () => {
  it("classifies a timed out execution as retryable TIMEOUT", () => {
    const error = toToolError("search", new Error("slow"), true);

    expect(error).toMatchObject({
      toolName: "search",
      code: ToolErrorCodes.TIMEOUT,
      message: "slow",
      retryable: true,
    });
    expect(typeof error.timestamp).toBe("number");
  });

  it("classifies a 400 HttpToolError as non-retryable bad_request", () => {
    const error = toToolError(
      "search",
      new HttpToolError(400, ToolErrorCodes.BAD_REQUEST, "bad request"),
      false,
    );

    expect(error.code).toBe("bad_request");
    expect(error.retryable).toBe(false);
    expect(error.message).toBe("bad request");
  });

  it("classifies a 500 HttpToolError as retryable http_error", () => {
    const error = toToolError(
      "search",
      new HttpToolError(500, ToolErrorCodes.HTTP_5XX, "server error"),
      false,
    );

    expect(error.code).toBe("http_error");
    expect(error.retryable).toBe(true);
  });

  it("classifies a TypeError as a retryable network error", () => {
    const error = toToolError("search", new TypeError("fetch failed"), false);

    expect(error.code).toBe("NETWORK_ERROR");
    expect(error.retryable).toBe(true);
    expect(error.message).toBe("fetch failed");
  });

  it("classifies a plain Error as a non-retryable unknown error", () => {
    const error = toToolError("search", new Error("boom"), false);

    expect(error.code).toBe("UNKNOWN");
    expect(error.retryable).toBe(false);
    expect(error.message).toBe("boom");
  });

  it("applies forced code and retryable overrides", () => {
    const error = toToolError("search", new Error("boom"), false, {
      code: ToolErrorCodes.INVALID_RESPONSE,
      retryable: true,
    });

    expect(error.code).toBe("INVALID_RESPONSE");
    expect(error.retryable).toBe(true);
    expect(error.message).toBe("boom");
  });

  it("applies forced overrides even when the execution timed out", () => {
    const error = toToolError("search", new Error("slow"), true, {
      code: ToolErrorCodes.CANCELLED,
      retryable: false,
    });

    expect(error.code).toBe("CANCELLED");
    expect(error.retryable).toBe(false);
  });
});

describe("isToolResult", () => {
  it("accepts an ok:true result", () => {
    expect(
      isToolResult({ ok: true, output: "OK", metadata: {}, complete: true }),
    ).toBe(true);
  });

  it("accepts an ok:false result", () => {
    expect(isToolResult({ ok: false, error: "failed", retryable: true })).toBe(
      true,
    );
  });

  it("rejects malformed values", () => {
    expect(isToolResult(null)).toBe(false);
    expect(isToolResult("nope")).toBe(false);
    expect(isToolResult({ ok: true, output: 1, metadata: {} })).toBe(false);
    expect(isToolResult({ ok: false, error: "failed", retryable: "yes" })).toBe(
      false,
    );
  });
});
