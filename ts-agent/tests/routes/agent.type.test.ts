import { describe, it, expect } from "vitest";
import { AgentInputSchema } from "../../src/routes/agent.type";

describe("AgentInputSchema", () => {
  it("parses a minimal valid input", () => {
    const result = AgentInputSchema.parse({ query: "hola" });

    expect(result).toEqual({ query: "hola" });
  });

  it("throws when query is missing", () => {
    expect(() => AgentInputSchema.parse({})).toThrow();
  });

  it("throws when query is an empty string", () => {
    expect(() => AgentInputSchema.parse({ query: "" })).toThrow();
  });

  it("throws when sessionId is an empty string", () => {
    expect(() => AgentInputSchema.parse({ query: "x", sessionId: "" })).toThrow();
  });

  it("accepts a positive integer top_k", () => {
    const result = AgentInputSchema.parse({ query: "x", top_k: 1 });

    expect(result.top_k).toBe(1);
  });

  it("rejects top_k equal to 0", () => {
    expect(() => AgentInputSchema.parse({ query: "x", top_k: 0 })).toThrow();
  });

  it("rejects a negative top_k", () => {
    expect(() => AgentInputSchema.parse({ query: "x", top_k: -1 })).toThrow();
  });

  it("rejects a non-integer top_k", () => {
    expect(() => AgentInputSchema.parse({ query: "x", top_k: 1.5 })).toThrow();
  });

  it("rejects a history entry with an unsupported role", () => {
    expect(() =>
      AgentInputSchema.parse({ query: "x", history: [{ role: "tool", content: "y" }] }),
    ).toThrow();
  });

  it("accepts a valid history array", () => {
    const result = AgentInputSchema.parse({
      query: "x",
      history: [
        { role: "user", content: "hi" },
        { role: "assistant", content: "hello" },
        { role: "system", content: "be nice" },
      ],
    });

    expect(result.history).toHaveLength(3);
  });

  it("strips unknown keys (zod v4 non-strict object)", () => {
    const result = AgentInputSchema.parse({ query: "x", unknownKey: "drop-me" });

    expect(result).toEqual({ query: "x" });
    expect(result).not.toHaveProperty("unknownKey");
  });
});
