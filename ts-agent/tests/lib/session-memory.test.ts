import { vi, describe, it, expect, beforeEach } from "vitest";

vi.mock("ioredis", () => ({
  Redis: class {
    on() {}
  },
}));

describe("session-memory", () => {
  let fakeClient: any;

  beforeEach(() => {
    const pipelineChain = {
      lpush: vi.fn().mockReturnThis(),
      ltrim: vi.fn().mockReturnThis(),
      expire: vi.fn().mockReturnThis(),
      exec: vi.fn().mockResolvedValue([]),
    };
    fakeClient = {
      pipeline: vi.fn(() => pipelineChain),
      lrange: vi.fn(),
      del: vi.fn(),
      exists: vi.fn(),
      ttl: vi.fn(),
    };
  });

  it("add uses defaults: ltrim 0,4 and expire 10800", async () => {
    const { SessionMemory } = await import("../../src/lib/session-memory.js");
    const sm = new SessionMemory(fakeClient, undefined as any);
    const msg = { role: "user" as const, content: "hi" };
    await sm.add("s1", msg);
    const pipe = fakeClient.pipeline();
    expect(fakeClient.pipeline).toHaveBeenCalled();
    expect(pipe.lpush).toHaveBeenCalledWith("session:s1", JSON.stringify(msg));
    expect(pipe.ltrim).toHaveBeenCalledWith("session:s1", 0, 4); // windowSize 5 -> 0,4
    expect(pipe.expire).toHaveBeenCalledWith("session:s1", 10800);
    expect(pipe.exec).toHaveBeenCalled();
  });

  it("add with custom config: ltrim 0,2 and expire 60", async () => {
    const { SessionMemory } = await import("../../src/lib/session-memory.js");
    const sm = new SessionMemory(fakeClient, { defaultWindowSize: 3, defaultTTLSeconds: 60 });
    const msg = { role: "assistant" as const, content: "ok" };
    await sm.add("s2", msg);
    const pipe = fakeClient.pipeline();
    expect(pipe.lpush).toHaveBeenCalledWith("session:s2", JSON.stringify(msg));
    expect(pipe.ltrim).toHaveBeenCalledWith("session:s2", 0, 2);
    expect(pipe.expire).toHaveBeenCalledWith("session:s2", 60);
  });

  it("getHistory returns reversed parsed messages and calls lrange", async () => {
    const { SessionMemory } = await import("../../src/lib/session-memory.js");
    const sm = new SessionMemory(fakeClient);
    fakeClient.lrange.mockResolvedValue([
      '{"role":"user","content":"a"}',
      '{"role":"assistant","content":"b"}',
    ]);
    const hist = await sm.getHistory("s1");
    expect(fakeClient.lrange).toHaveBeenCalledWith("session:s1", 0, -1);
    expect(hist).toEqual([
      { role: "assistant", content: "b" },
      { role: "user", content: "a" },
    ]);
  });

  it("getHistory returns [] when lrange rejects", async () => {
    const { SessionMemory } = await import("../../src/lib/session-memory.js");
    const sm = new SessionMemory(fakeClient);
    fakeClient.lrange.mockRejectedValue(new Error("boom"));
    const hist = await sm.getHistory("s1");
    expect(hist).toEqual([]);
  });

  it("clear returns true if del>0, false if del==0", async () => {
    const { SessionMemory } = await import("../../src/lib/session-memory.js");
    const sm = new SessionMemory(fakeClient);
    fakeClient.del.mockResolvedValueOnce(1);
    expect(await sm.clear("s1")).toBe(true);
    fakeClient.del.mockResolvedValueOnce(0);
    expect(await sm.clear("s2")).toBe(false);
    expect(fakeClient.del).toHaveBeenNthCalledWith(1, "session:s1");
    expect(fakeClient.del).toHaveBeenNthCalledWith(2, "session:s2");
  });

  it("exists returns true if 1, false if 0", async () => {
    const { SessionMemory } = await import("../../src/lib/session-memory.js");
    const sm = new SessionMemory(fakeClient);
    fakeClient.exists.mockResolvedValueOnce(1);
    expect(await sm.exists("s1")).toBe(true);
    fakeClient.exists.mockResolvedValueOnce(0);
    expect(await sm.exists("s2")).toBe(false);
  });

  it("getTTL returns client ttl", async () => {
    const { SessionMemory } = await import("../../src/lib/session-memory.js");
    const sm = new SessionMemory(fakeClient);
    fakeClient.ttl.mockResolvedValue(42);
    expect(await sm.getTTL("s1")).toBe(42);
    expect(fakeClient.ttl).toHaveBeenCalledWith("session:s1");
  });
});
