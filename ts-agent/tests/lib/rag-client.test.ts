import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

const base = process.env.RAG_URL || "http://localhost:8000/rag";

describe("rag-client", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("search calls POST /search with correct body and returns payload", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    const payload = { context: "ctx", citations: [] };
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    });

    const result = await httpClient.search("q", { topK: 7, domain: "d", topic: "t" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe(`${base}/search`);
    const opts = call[1] as any;
    expect(opts.method).toBe("POST");
    expect(opts.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(opts.body)).toEqual({
      query: "q",
      domain: "d",
      topic: "t",
      top_k: 7,
    });
    expect(result).toEqual(payload);
  });

  it("search without topic/topK uses topic:null and top_k:5", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ context: "", citations: [] }),
    });

    await httpClient.search("q", { domain: "d" } as any);
    const call = fetchMock.mock.calls[0];
    const opts = call[1] as any;
    expect(JSON.parse(opts.body)).toEqual({
      query: "q",
      domain: "d",
      topic: null,
      top_k: 5,
    });
  });

  it("search non-ok rejects with /RAG search failed: 500/", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });

    await expect(httpClient.search("q", { domain: "d" } as any)).rejects.toThrow(/RAG search failed: 500/);
  });

  it("ingest posts to /ingest/job with correct body", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    const jobPayload = { status: "queued", url: "http://x", job_id: "123" };
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => jobPayload,
    });

    const data = { url: "http://x", source: "s", domain: "d", topic: "t" };
    const res = await httpClient.ingest(data as any);
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe(`${base}/ingest/job`);
    const opts = call[1] as any;
    expect(opts.method).toBe("POST");
    expect(opts.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(opts.body)).toEqual({ url: data.url, domain: data.domain, topic: data.topic });
    expect(res).toEqual(jobPayload);
  });

  it("ingest non-ok rejects with /Ingest File Job failed/", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });

    await expect(httpClient.ingest({ url: "u", source: "s", domain: "d", topic: "t" } as any)).rejects.toThrow(/Ingest File Job failed/);
  });

  it("deleteDocument DELETEs encoded path", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "deleted", source: "a/b c" }),
    });

    const res = await httpClient.deleteDocument("a/b c");
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe(`${base}/documents/a%2Fb%20c`);
    const opts = call[1] as any;
    expect(opts.method).toBe("DELETE");
    expect(res).toEqual({ status: "deleted", source: "a/b c" });
  });

  it("listSources POSTs /documents with domain body", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "success", metadata: { documents: [], count: 0 }, output: "ok" }),
    });

    await httpClient.listSources("dom");
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe(`${base}/documents`);
    const opts = call[1] as any;
    expect(opts.method).toBe("POST");
    expect(opts.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(opts.body)).toEqual({ domain: "dom" });
  });

  it("getSourceMetadata GETs /documents/metadata with encoded source", async () => {
    const { httpClient } = await import("../../src/lib/rag-client.js");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "success", metadata: {}, output: "ok" }),
    });

    await httpClient.getSourceMetadata("a/b");
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe(`${base}/documents/metadata?source=a%2Fb`);
    const opts = call[1] as any;
    expect(opts.method).toBe("GET");
  });
});
