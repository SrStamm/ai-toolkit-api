import { describe, it, expect } from "vitest";
import type { RagPath } from "@ai-toolkit/rag-contracts";
import {
  RAG_PATHS,
  fromDeleteDocumentResponse,
  fromDocumentMetadataResponse,
  fromIngestJobResponse,
  fromListDocumentsResponse,
  fromSearchResponse,
  toOriginBaseUrl,
  toWireIngest,
  toWireSearch,
} from "../../src/adapters/rag-contracts.js";

// Compile-time assertion: every adapter path is a generated contract path.
const typedPaths: Record<string, RagPath> = RAG_PATHS;
void typedPaths;

describe("rag-contracts adapter", () => {
  it("uses only generated RAG paths", () => {
    expect(Object.values(RAG_PATHS)).toEqual([
      "/rag/search",
      "/rag/documents",
      "/rag/documents/{source}",
      "/rag/documents/metadata",
      "/rag/ingest/job",
      "/rag/job/{job_id}",
    ]);
  });

  it("toWireSearch applies wire defaults", () => {
    expect(toWireSearch("q", { domain: "d" })).toEqual({
      query: "q",
      domain: "d",
      topic: null,
      top_k: 5,
    });
    expect(toWireSearch("q", { domain: "d", topic: "t", topK: 7 })).toEqual({
      query: "q",
      domain: "d",
      topic: "t",
      top_k: 7,
    });
  });

  it("toWireIngest maps source to replaces_source", () => {
    expect(
      toWireIngest({
        url: "https://example.com/doc",
        source: "legacy-source",
        domain: "d",
        topic: "t",
      }),
    ).toEqual({
      url: "https://example.com/doc",
      domain: "d",
      topic: "t",
      replaces_source: "legacy-source",
    });
  });

  it("fromSearchResponse keeps string citations unchanged", () => {
    expect(
      fromSearchResponse({ context: "ctx", citations: ["src-a", "src-b"] }),
    ).toEqual({ context: "ctx", citations: ["src-a", "src-b"] });
  });

  it("fromIngestJobResponse keeps queued status and job_id", () => {
    expect(fromIngestJobResponse({ status: "queued", job_id: "J-1" })).toEqual({
      status: "queued",
      job_id: "J-1",
    });
  });

  it("fromDeleteDocumentResponse keeps deleted source", () => {
    expect(fromDeleteDocumentResponse({ status: "deleted", source: "a/b" })).toEqual(
      { status: "deleted", source: "a/b" },
    );
  });

  it("fromListDocumentsResponse maps every document field", () => {
    const payload = {
      status: "success" as const,
      metadata: {
        documents: [
          {
            source: "src-a",
            display_name: null,
            domain: "d",
            topic: "t",
            chunk_count: 3,
            last_ingested: 123,
          },
        ],
        count: 1,
      },
      output: "Found 1 document(s):",
    };

    expect(fromListDocumentsResponse(payload)).toEqual(payload);
  });

  it("fromDocumentMetadataResponse maps metadata", () => {
    const payload = {
      status: "success" as const,
      metadata: {
        source: "src-a",
        display_name: "Friendly name",
        domain: "d",
        topic: "t",
        chunk_count: 2,
        last_ingested: 456,
      },
      output: "OK",
    };

    expect(fromDocumentMetadataResponse(payload)).toEqual(payload);
  });

  it("toOriginBaseUrl strips the legacy /rag suffix", () => {
    expect(toOriginBaseUrl("http://host:8000/rag")).toBe("http://host:8000");
    expect(toOriginBaseUrl("http://host:8000/rag/")).toBe("http://host:8000");
    expect(toOriginBaseUrl("http://host:8000")).toBe("http://host:8000");
  });
});
