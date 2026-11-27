/**
 * The only module allowed to import the generated RAG contract.
 *
 * Wire types are read from `@ai-toolkit/rag-contracts` and converted into the
 * agent-owned models in `src/types/rag-api.ts`. Callers only see agent models.
 */

import type {
  DeleteDocumentResponse as WireDeleteDocumentResponse,
  DocumentMetadataResponse as WireDocumentMetadataResponse,
  IngestJobResponse as WireIngestJobResponse,
  IngestRequest as WireIngestRequest,
  ListDocumentsResponse as WireListDocumentsResponse,
  RagPath,
  SearchRequest as WireSearchRequest,
  SearchResponse as WireSearchResponse,
} from "@ai-toolkit/rag-contracts";
import type {
  DeleteDocumentResponse,
  DocumentMetadataResponse,
  IngestData,
  IngestJobResponse,
  ListDocumentsResponse,
  SearchOptions,
  SearchResult,
  SourceMetadata,
} from "../types/rag-api";

type WireSourceMetadata = WireListDocumentsResponse["metadata"]["documents"][number];

const DEFAULT_TOP_K = 5;

export const RAG_PATHS = {
  search: "/rag/search",
  documents: "/rag/documents",
  document: "/rag/documents/{source}",
  metadata: "/rag/documents/metadata",
  ingestJob: "/rag/ingest/job",
  jobStatus: "/rag/job/{job_id}",
} as const satisfies Record<string, RagPath>;

/** Accept both an origin and the legacy `.../rag` value used in current .env files. */
export function toOriginBaseUrl(url: string): string {
  return url.replace(/\/rag\/?$/, "").replace(/\/$/, "");
}

export function toWireSearch(query: string, opts: SearchOptions): WireSearchRequest {
  return {
    query,
    domain: opts.domain,
    topic: opts.topic ?? null,
    top_k: opts.topK ?? DEFAULT_TOP_K,
  };
}

export function fromSearchResponse(payload: unknown): SearchResult {
  const wire = payload as WireSearchResponse;
  return { context: wire.context, citations: wire.citations };
}

export function toWireIngest(data: IngestData): WireIngestRequest {
  return {
    url: data.url,
    domain: data.domain,
    topic: data.topic,
    replaces_source: data.source,
  };
}

export function fromIngestJobResponse(payload: unknown): IngestJobResponse {
  const wire = payload as WireIngestJobResponse;
  return { status: wire.status, job_id: wire.job_id };
}

export function fromDeleteDocumentResponse(payload: unknown): DeleteDocumentResponse {
  const wire = payload as WireDeleteDocumentResponse;
  return { status: wire.status, source: wire.source };
}

export function fromListDocumentsResponse(payload: unknown): ListDocumentsResponse {
  const wire = payload as WireListDocumentsResponse;
  return {
    status: wire.status,
    metadata: {
      documents: wire.metadata.documents.map(toSourceMetadata),
      count: wire.metadata.count,
    },
    output: wire.output,
  };
}

export function fromDocumentMetadataResponse(payload: unknown): DocumentMetadataResponse {
  const wire = payload as WireDocumentMetadataResponse;
  return {
    status: wire.status,
    metadata: toSourceMetadata(wire.metadata),
    output: wire.output,
  };
}

function toSourceMetadata(wire: WireSourceMetadata): SourceMetadata {
  return {
    source: wire.source,
    display_name: wire.display_name,
    domain: wire.domain,
    topic: wire.topic,
    chunk_count: wire.chunk_count,
    last_ingested: wire.last_ingested,
  };
}
