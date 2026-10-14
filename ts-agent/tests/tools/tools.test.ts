import { vi, describe, it, expect, beforeEach } from "vitest";
import { z } from "zod";

vi.mock("../../src/lib/rag-client", () => ({
  httpClient: {
    search: vi.fn(),
    ingest: vi.fn(),
    deleteDocument: vi.fn(),
    listSources: vi.fn(),
    getSourceMetadata: vi.fn(),
  },
}));

describe("tools registry and tools", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("registry lists 5 tools and getTool works", async () => {
    // Import tools (side-effect) and registry
    await import("../../src/tools/index.js");
    const { getTool, listTools } = await import("../../src/tools/registry.js");
    const names = listTools().map((t) => t.name).sort();
    expect(names).toEqual([
      "delete_document",
      "get_document_metadata",
      "ingest_document",
      "list_documents",
      "retrieve_context",
    ]);
    expect(getTool("retrieve_context")).toBeDefined();
    expect(getTool("nope")).toBeUndefined();
  });

  describe("retrieve_context", () => {
    it("returns ok with context when search succeeds", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.search as any).mockResolvedValue({
        context: "CTX",
        citations: [{ source: "s", chunk_index: 0, text: "t" }],
      });
      const tool = getTool("retrieve_context");
      const res = await tool!.execute(
        { query: "q", domain: "", top_k: undefined, topic: undefined } as any,
        {} as any,
      );
      expect(httpClient.search).toHaveBeenCalledWith("q", {
        topK: undefined,
        domain: "",
        topic: undefined,
      });
      expect(res).toEqual({
        ok: true,
        output: "CTX",
        metadata: { citations: [{ source: "s", chunk_index: 0, text: "t" }] },
      });
      expect((res as any).metadata.citations.length).toBe(1);
    });

    it("returns ok with the Spanish no-results message when search returns empty context", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.search as any).mockResolvedValue({ context: "", citations: [] });
      const tool = getTool("retrieve_context");
      const res = await tool!.execute(
        { query: "q", domain: "", top_k: undefined, topic: undefined } as any,
        {} as any,
      );
      expect(res).toEqual({
        ok: true,
        output:
          "No se encontró contexto relevante en la base de conocimientos para esta consulta.",
        metadata: { citations: [] },
      });
    });
  });

  describe("list_documents", () => {
    it("returns ok:false retryable:false when status failed", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.listSources as any).mockResolvedValue({ status: "failed" });
      const tool = getTool("list_documents");
      const res = await tool!.execute({ domain: "d" } as any, {} as any);
      expect(res).toEqual({ ok: false, retryable: false, error: "No hay documentos en la base de conocimiento" });
    });

    it("returns ok:true with metadata on success", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.listSources as any).mockResolvedValue({
        status: "success",
        metadata: { documents: [{ source: "s" }], count: 1 },
        output: "OUT",
      });
      const tool = getTool("list_documents");
      const res = await tool!.execute({ domain: "d" } as any, {} as any);
      expect(res).toEqual({
        ok: true,
        output: "OUT",
        metadata: { documents: [{ source: "s" }], count: 1 },
      });
    });
  });

  describe("get_document_metadata", () => {
    it("returns ok:false retryable:false when status failed", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.getSourceMetadata as any).mockResolvedValue({ status: "failed" });
      const tool = getTool("get_document_metadata");
      const res = await tool!.execute({ source: "src" } as any, {} as any);
      expect(res).toEqual({ ok: false, retryable: false, error: 'No existe metadata para "src"' });
    });

    it("returns ok:true with metadata on success", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.getSourceMetadata as any).mockResolvedValue({
        status: "success",
        metadata: { source: "s" },
        output: "OUT",
      });
      const tool = getTool("get_document_metadata");
      const res = await tool!.execute({ source: "src" } as any, {} as any);
      expect(res).toEqual({ ok: true, output: "OUT", metadata: { source: "s" } });
    });
  });

  describe("delete_document", () => {
    it("returns ok:true with source info", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.deleteDocument as any).mockResolvedValue({ status: "deleted", source: "src-1" });
      const tool = getTool("delete_document");
      const res = await tool!.execute({ source: "src-1" } as any, {} as any);
      expect(res.ok).toBe(true);
      expect((res as any).output).toContain("src-1");
      expect((res as any).metadata.source).toBe("src-1");
    });
  });

  describe("ingest_document", () => {
    it("returns ok:true complete:true with job_id", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.ingest as any).mockResolvedValue({ job_id: "JOB-1", status: "queued" } as any);
      const tool = getTool("ingest_document");
      const res = await tool!.execute(
        { url: "https://example.com", domain: "d", topic: "t" } as any,
        {} as any,
      );
      expect(res.ok).toBe(true);
      expect((res as any).complete).toBe(true);
      expect((res as any).output).toContain("JOB-1");
      expect((res as any).metadata.job_id).toBe("JOB-1");
    });

    it("surfaces the queued job response contract (status + job_id)", async () => {
      await import("../../src/tools/index.js");
      const { getTool } = await import("../../src/tools/registry.js");
      const { httpClient } = await import("../../src/lib/rag-client.js");
      (httpClient.ingest as any).mockResolvedValue({
        status: "queued",
        url: "https://example.com",
        job_id: "JOB-1",
      });
      const tool = getTool("ingest_document");
      const res = await tool!.execute(
        { url: "https://example.com", domain: "d", topic: "t" } as any,
        {} as any,
      );
      expect(res).toEqual({
        ok: true,
        complete: true,
        output: "Ingestion job queued. Job ID: JOB-1",
        metadata: { job_id: "JOB-1", status: "queued" },
      });
    });
  });
});
